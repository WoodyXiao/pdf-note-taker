import React from "react";
import {
  Bold,
  Italic,
  Underline,
  Code,
  List,
  ListOrdered,
  Heading1,
  Heading2,
  Heading3,
  Highlighter,
  Sparkles,
} from "lucide-react";
import axios from "axios";
import { toast } from "sonner";

function EditorExtension({ editor, fileId, notebookId, onRequestSaveNow }) {
  if (!editor) return null;

  const onAIClick = async () => {
    const token = localStorage.getItem("authToken");
    if (!token) {
      toast.error("Please login again.");
      return;
    }

    const selectedText = editor.state.doc.textBetween(
      editor.state.selection.from,
      editor.state.selection.to,
      " "
    );

    if (!selectedText || !selectedText.trim()) {
      toast("Please select a question in the editor first.");
      return;
    }

    toast("AI is getting your answer...");

    try {
      // If we are inside a notebook, persist the user-side question as a chat message
      if (notebookId) {
        await axios.post(
          `/api/files/notebooks/${notebookId}/messages/`,
          {
            role: "user",
            channel: "editor_assist",
            contentHtml: selectedText,
            metadata: {
              selected_text: selectedText,
            },
          },
          {
            headers: {
              Authorization: `Token ${token}`,
            },
          }
        );
      }

      const res = await axios.post(
        "/api/ai/answer/",
        {
          question: selectedText,
          // Prefer notebook-level RAG when notebookId is provided.
          ...(notebookId ? { notebookId } : { fileId }),
          channel: "editor_assist",
          selectedText,
        },
        {
          headers: {
            Authorization: `Token ${token}`,
          },
        }
      );

      const finalText = res.data.html || "";
      // Append the answer to the end of the note.
      editor
        .chain()
        .focus()
        .insertContent(`<p><strong>Answer (AI):</strong></p>${finalText}`)
        .run();

      // Critical: persist immediately so logout / route change won't lose it.
      if (typeof onRequestSaveNow === "function") {
        await onRequestSaveNow();
      }
    } catch (e) {
      console.error(e);
      toast.error("AI request failed");
    }
  };

  return (
    <div className="editor-toolbar" style={{ padding: 16 }}>
      <div className="button-group" style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className={editor.isActive("heading", { level: 1 }) ? "text-blue-500" : ""}
        >
          <Heading1 />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={editor.isActive("heading", { level: 2 }) ? "text-blue-500" : ""}
        >
          <Heading2 />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={editor.isActive("heading", { level: 3 }) ? "text-blue-500" : ""}
        >
          <Heading3 />
        </button>

        <button
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={editor.isActive("bold") ? "text-blue-500" : ""}
        >
          <Bold />
        </button>

        <button
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={editor.isActive("italic") ? "text-blue-500" : ""}
        >
          <Italic />
        </button>

        <button
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          className={editor.isActive("underline") ? "text-blue-500" : ""}
        >
          <Underline />
        </button>

        <button
          onClick={() => editor.chain().focus().toggleCode().run()}
          className={editor.isActive("code") ? "text-blue-500" : ""}
        >
          <Code />
        </button>

        <button
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={editor.isActive("bulletList") ? "text-blue-500" : ""}
        >
          <List />
        </button>

        <button
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={editor.isActive("orderedList") ? "text-blue-500" : ""}
        >
          <ListOrdered />
        </button>

        <input
          type="color"
          onInput={(event) =>
            editor.chain().focus().setColor(event.target.value).run()
          }
          value={editor.getAttributes("textStyle").color || "#000000"}
          data-testid="setColor"
        />

        <button
          onClick={() => editor.chain().focus().toggleHighlight().run()}
          className={editor.isActive("highlight") ? "text-blue-500" : ""}
        >
          <Highlighter />
        </button>

        <button onClick={onAIClick} className="hover:text-blue-500">
          <Sparkles />
        </button>
      </div>
    </div>
  );
}

export default EditorExtension;


