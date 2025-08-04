"use client";
import {
  Dialog,
  DialogTrigger,
  DialogHeader,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAction, useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { useState } from "react";
import { Loader2Icon } from "lucide-react";
import uuid4 from "uuid4";
import { useUser } from "@clerk/nextjs";
import axios from "axios";

export function UploadPdfDialog({ children }) {
  const generateUploadUrl = useMutation(api.fileStorage.generateUploadUrl);
  const addFileEntryToDB = useMutation(api.fileStorage.addFileEntryToDB);
  const getFileUrl = useMutation(api.fileStorage.getFileUrl);

  const embeddDocument = useAction(api.myAction.ingest);

  const { user } = useUser();

  const [file, setFile] = useState();
  const [fileName, setFileName] = useState();
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const OnFileSelect = (event) => {
    setFile(event.target.files[0]);
  };

  const OnUpload = async () => {
    setLoading(true);

    // 1. get a short-lived upload url.
    const postUrl = await generateUploadUrl();

    // 2. post the file to the url.
    const result = await fetch(postUrl, {
      method: "POST",
      headers: { "Content-Type": file?.type },
      body: file,
    });

    const { storageId } = await result.json();
    const fileId = uuid4();
    const fileUrl = await getFileUrl({ storageId: storageId });

    // 3. Save the newly allocated storage id to the DB.
    const res = await addFileEntryToDB({
      fileId: fileId,
      storageId: storageId,
      fileName: fileName ?? "Untitled File",
      fileUrl: fileUrl,
      createdBy: user?.primaryEmailAddress?.emailAddress,
    });

    // 4. API call to fetch pdf process data.
    const apiRes = await axios.get("/api/pdf-loader?pdfUrl=" + fileUrl);

    await embeddDocument({
      splitText: apiRes.data.result
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
      fileId: fileId,
    });

    setLoading(false);
    setOpen(false);
  };

  return (
    <Dialog open={open}>
      <DialogTrigger asChild>
        <Button className="w-full" onClick={() => setOpen(true)}>
          + Upload PFD File
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload PDF File</DialogTitle>
          <DialogDescription asChild>
            <div>
              <h2>Select a file to Upload</h2>
              <div className="gap-2 p-3 rounded-md border">
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(event) => OnFileSelect(event)}
                />
              </div>

              <div className="mt-2">
                <label>File Name *</label>
                <Input
                  placeholder="File Name"
                  onChange={(e) => setFileName(e.target.value)}
                />
              </div>
            </div>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="sm:justify-end">
          <DialogClose asChild>
            <Button
              type="button"
              variant={"secondary"}
              onClick={() => setOpen(false)}
            >
              Close
            </Button>
          </DialogClose>
          <Button onClick={OnUpload} disabled={loading}>
            {loading ? <Loader2Icon className="animate-spin" /> : "Upload"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
