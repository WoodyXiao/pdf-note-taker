"use client";

import { useQuery } from "convex/react";
import { useParams } from "next/navigation";
import WorkspaceHeader from "../_components/WorkspaceHeader";
import { api } from "../../../convex/_generated/api";
import { useEffect } from "react";
import PdfViewer from "../_components/PdfViewer";
import TextEditor from "../_components/TextEditor";

function Workspace() {
  const { fileId } = useParams();
  const fileInfo = useQuery(api.fileStorage.getFileRecord, {
    fileId: fileId,
  });

  useEffect(() => {
    console.log(fileInfo);
  }, [fileInfo]);

  if (!fileInfo) return <div>Loading...</div>;

  return (
    <div>
      <WorkspaceHeader />
      <div className="grid grid-cols-2 gap-5">
        <div>
          <TextEditor />
        </div>
        <div>
          <PdfViewer fileUrl={fileInfo?.fileUrl} />
        </div>
      </div>
    </div>
  );
}

export default Workspace;
