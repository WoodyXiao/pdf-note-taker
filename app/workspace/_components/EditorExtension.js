import { api } from "@/convex/_generated/api";
import { useAction } from "convex/react";
import {
  Bold,
  Italic,
  Underline,
  Code,
  List,
  Heading1,
  Heading2,
  Heading3,
  ListOrdered,
  Highlighter,
  Sparkles,
} from "lucide-react";
import React from "react";
import { useParams } from "next/navigation";

function EditorExtension({ editor }) {
  const { fileId } = useParams();

  const SearchAI = useAction(api.myAction.search);

  const onAIClick = async () => {
    const selectedText = editor.state.doc.textBetween(
      editor.state.selection.from,
      editor.state.selection.to,
      " "
    );

    const result = await SearchAI({
      query: selectedText,
      fileId: fileId,
    });

    const UnformattedAns = JSON.parse(result);
    let AllUnformattedanswer = "";
    UnformattedAns &&
      UnformattedAns.forEach((item) => {
        AllUnformattedanswer = AllUnformattedanswer + item.pageContent;
      });

    const PROMPT = `For question : ${selectedText} and with the given content as answer, please give appropriate answer in HTML format. The answer content is ${AllUnformattedanswer}`;
  
    
  };

  return (
    editor && (
      <div className="p-5">
        <div className="control-group">
          <div className="button-group flex gap-3">
            <button
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 1 }).run()
              }
              className={
                editor.isActive("heading", { level: 1 }) ? "text-blue-500" : ""
              }
            >
              <Heading1 />
            </button>
            <button
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 2 }).run()
              }
              className={
                editor.isActive("heading", { level: 2 }) ? "text-blue-500" : ""
              }
            >
              <Heading2 />
            </button>
            <button
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 3 }).run()
              }
              className={
                editor.isActive("heading", { level: 3 }) ? "text-blue-500" : ""
              }
            >
              <Heading3 />
            </button>

            <button
              onClick={() => editor.chain().focus().toggleBold().run()}
              className={editor?.isActive("bold") ? "text-blue-500" : ""}
            >
              <Bold />
            </button>

            <button
              onClick={() => editor.chain().focus().toggleItalic().run()}
              className={editor?.isActive("italic") ? "text-blue-500" : ""}
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
              value={editor.getAttributes("textStyle").color}
              data-testid="setColor"
            />

            <button
              onClick={() => editor.chain().focus().toggleHighlight().run()}
              className={editor.isActive("highlight") ? "text-blue-500" : ""}
            >
              <Highlighter />
            </button>

            <button
              onClick={() => onAIClick()}
              className={"hover:text-blue-500"}
            >
              <Sparkles />
            </button>
          </div>
        </div>
      </div>
    )
  );
}

export default EditorExtension;
