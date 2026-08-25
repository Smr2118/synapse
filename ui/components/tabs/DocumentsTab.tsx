"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { MetricCard } from "@/components/MetricCard";
import { callApi } from "@/lib/api";
import { Trash2 } from "lucide-react";

interface DocumentInfo {
  document_id: string;
  chunks: number;
}

export function DocumentsTab({ apiUrl }: { apiUrl: string }) {
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<DocumentInfo[] | null>(null);
  const [totals, setTotals] = useState({ total_documents: 0, total_chunks: 0 });
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [deleteMsg, setDeleteMsg] = useState<string | null>(null);

  async function handleRefresh() {
    setLoading(true);
    setError(null);
    setDeleteMsg(null);
    const { status, data } = await callApi("GET", `${apiUrl}/documents`);
    setLoading(false);
    if (status === 200) {
      setDocuments(data.documents as DocumentInfo[]);
      setTotals({
        total_documents: data.total_documents as number,
        total_chunks: data.total_chunks as number,
      });
    } else {
      setError((data as Record<string, string>).detail ?? JSON.stringify(data));
    }
  }

  async function handleDelete(docId: string) {
    setDeleting(docId);
    setDeleteMsg(null);
    const { status, data } = await callApi("DELETE", `${apiUrl}/documents/${encodeURIComponent(docId)}`);
    setDeleting(null);
    if (status === 200) {
      setDeleteMsg(`Deleted ${data.deleted_chunks as number} chunks from "${docId}"`);
      handleRefresh();
    } else {
      setError((data as Record<string, string>).detail ?? JSON.stringify(data));
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Indexed documents</h2>
        <p className="text-sm text-muted-foreground">
          Lists every document in Pinecone with its chunk count.
        </p>
      </div>

      <Button onClick={handleRefresh} disabled={loading}>
        {loading ? "Loading…" : "Refresh"}
      </Button>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      {deleteMsg && (
        <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
          <AlertDescription>{deleteMsg}</AlertDescription>
        </Alert>
      )}

      {documents && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-2 max-w-xs">
            <MetricCard label="Total documents" value={totals.total_documents} />
            <MetricCard label="Total chunks" value={totals.total_chunks} />
          </div>

          {documents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No documents indexed yet.</p>
          ) : (
            <div className="rounded-lg border divide-y">
              {documents.map((doc) => (
                <div key={doc.document_id} className="flex items-center justify-between px-4 py-2 text-sm">
                  <span className="font-mono truncate flex-1">{doc.document_id}</span>
                  <span className="text-muted-foreground text-xs mx-4">{doc.chunks} chunks</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(doc.document_id)}
                    disabled={deleting === doc.document_id}
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
