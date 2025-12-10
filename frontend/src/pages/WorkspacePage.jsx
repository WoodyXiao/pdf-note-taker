import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import TextEditor from "../components/TextEditor";

function WorkspacePage() {
  const { fileId } = useParams();
  const [fileInfo, setFileInfo] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("authToken");
    axios
      .get(`/api/files/${fileId}/`, {
        headers: {
          Authorization: `Token ${token}`,
        },
      })
      .then((res) => setFileInfo(res.data))
      .catch(() => setFileInfo(null));
  }, [fileId]);

  if (!fileInfo) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <div
        style={{
          padding: 16,
          display: "flex",
          justifyContent: "space-between",
          borderBottom: "1px solid #eee",
        }}
      >
        <div>PDF Note Taker</div>
        <h2 style={{ fontWeight: "bold" }}>{fileInfo.file_name}</h2>
      </div>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          padding: 16,
        }}
      >
        <div>
          <TextEditor fileId={fileId} />
        </div>
        <div>
          <iframe
            src={fileInfo.file_url + "#toolbar=0"}
            height="90vh"
            width="100%"
            style={{ border: "none" }}
          />
        </div>
      </div>
    </div>
  );
}

export default WorkspacePage;



