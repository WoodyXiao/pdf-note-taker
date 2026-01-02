import React, { useCallback, useEffect, useRef } from "react";
import axios from "axios";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Highlight from "@tiptap/extension-highlight";
import Placeholder from "@tiptap/extension-placeholder";
import TextStyle from "@tiptap/extension-text-style";
import Color from "@tiptap/extension-color";
import EditorExtension from "./EditorExtension";

function TextEditor({ fileId, notebookId }) {
  const saveTimerRef = useRef(null);

  const editor = useEditor({
    extensions: [
      TextStyle,
      StarterKit,
      Highlight,
      Color,
      Placeholder.configure({
        placeholder: "Taking notes here....",
      }),
    ],
    content: "",
    editorProps: {
      attributes: {
        class:
          "tiptap h-screen p-5 focus:outline-none leading-relaxed text-base",
      },
    },
  });

  const saveNow = useCallback(async () => {
    if (!editor || !notebookId) return;

    // If there's a pending debounce, cancel it and save immediately.
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }

    const token = localStorage.getItem("authToken");
    if (!token) return;

    const json = editor.getJSON();
    try {
      await axios.put(
        `/api/files/notebooks/${notebookId}/content/`,
        {
          pages: [
            {
              title: "Main",
              order_index: 0,
              content: json,
            },
          ],
        },
        {
          headers: { Authorization: `Token ${token}` },
        }
      );
    } catch (err) {
      console.error("Failed to save notebook content", err);
    }
  }, [editor, notebookId]);

  // Load existing notebook content on mount.
  useEffect(() => {
    if (!editor || !notebookId) return;

    const token = localStorage.getItem("authToken");
    if (!token) return;

    axios
      .get(`/api/files/notebooks/${notebookId}/content/`, {
        headers: { Authorization: `Token ${token}` },
      })
      .then((res) => {
        const pages = res.data?.pages || [];
        const first = pages[0];
        if (first && first.content) {
          editor.commands.setContent(first.content);
        } else {
          editor.commands.clearContent();
        }
      })
      .catch((err) => {
        console.error("Failed to load notebook content", err);
      });
  }, [editor, notebookId]);

  // Autosave content with a small debounce.
  useEffect(() => {
    if (!editor || !notebookId) return;

    const onUpdate = () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
      // Save 2s after the last change.
      saveTimerRef.current = setTimeout(() => {
        saveNow();
      }, 2000);
    };

    editor.on("update", onUpdate);

    return () => {
      editor.off("update", onUpdate);
      // If we have a pending save, flush it before unmounting (best-effort).
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
        saveTimerRef.current = null;
        saveNow();
      }
    };
  }, [editor, notebookId, saveNow]);

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <EditorExtension
        editor={editor}
        fileId={fileId}
        notebookId={notebookId}
        onRequestSaveNow={saveNow}
      />
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflow: "auto",
          border: "1px solid #eee",
        }}
      >
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}

export default TextEditor;


