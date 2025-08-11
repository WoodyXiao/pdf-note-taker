import React from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Highlight from "@tiptap/extension-highlight";
import Placeholder from "@tiptap/extension-placeholder";
import TextStyle from "@tiptap/extension-text-style";
import Color from "@tiptap/extension-color";
import EditorExtension from "./EditorExtension";

function TextEditor() {
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

  return (
    <div>
      <EditorExtension editor={editor} />
      <div className="overflow-scroll h-[88vh]">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}

export default TextEditor;
