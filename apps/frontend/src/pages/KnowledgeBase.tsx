// apps/frontend/src/pages/KnowledgeBase.tsx
import React, { useEffect, useState } from "react";

// Types: Mirror backend schemas (Pydantic models defined in backend vectors.py)
interface KnowledgeBaseDocument {
  id: string; // "userid::title" combined key
  title: string;
  chunk_count: number;
}

interface DocumentListResponse {
  status: string;
  documents: KnowledgeBaseDocument[];
}

const KnowledgeBase: React.FC = () => {
  // State Management
  const [documents, setDocuments] = useState<KnowledgeBaseDocument[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setIsLoading(true);
    setError(null);

    // 4. FIX: Use the actual storage key from App.tsx/Login.tsx
    // (This was previously looking for 'lumenly_auth_token')
    const token = localStorage.getItem("access_token");

    if (!token) {
      setError("You must be logged in to manage the knowledge base.");
      setIsLoading(false);
      return;
    }

    try {
      // Perform the authenticated GET request to the backend aggregation endpoint
      const response = await fetch("http://localhost:8000/api/v1/vectors/documents", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`, // Pass JWT for Depends(get_current_user)
        },
      });

      const data: DocumentListResponse = await response.json();

      if (response.ok && data.status === "success") {
        setDocuments(data.documents);
        console.log(
          `KnowledgeBase UI: Retrieved ${data.documents.length} unique documents for user.`,
        );
      } else {
        // Handle explicit backend errors (e.g., status 500/503 from FastAPI)
        throw new Error(data.status || "Failed to retrieve documents.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
      console.error("KnowledgeBase UI Fetch Error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetching Logic on Component Mount
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDocuments();
  }, []);

  // -------------------------------------------------------------
  // Step 3, Task D/E: Action Handlers (Mocked for now)
  // -------------------------------------------------------------
  const handleDelete = (docId: string, docTitle: string) => {
    const combinedKey = docId; // "userid::title"
    alert(
      `MOCK: DELETE requested for Document Title: "${docTitle}". (Internal Key: ${combinedKey})`,
    );
    // After confirmation, we would run fetch(/api/vectors/delete/{combinedKey}, {method: 'DELETE'})
    // and re-call fetchDocuments() on success.
  };

  const handleReindex = (docTitle: string) => {
    alert(`MOCK: RE-INDEX requested for "${docTitle}". This would trigger parsing again.`);
  };

  // -------------------------------------------------------------
  // Render UI using Tailwind CSS (Retained from previous turn)
  // -------------------------------------------------------------
  return (
    <div className="container mx-auto px-4 py-8 bg-gray-50/50 min-h-full">
      <div className="flex justify-between items-center mb-8 border-b pb-4 border-gray-200">
        <h1 className="text-3xl font-bold text-gray-800">Knowledge Base Dashboard</h1>
        <button
          onClick={fetchDocuments}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 transition duration-150 shadow-sm font-medium"
        >
          {isLoading ? "Refreshing..." : "🔄 Refresh List"}
        </button>
      </div>

      {isLoading ? (
        // Loading State
        <div className="text-center py-20 text-gray-600">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          Scanning Qdrant payloads for unique documents...
        </div>
      ) : error ? (
        // Error State
        <div className="bg-red-50 border border-red-200 text-red-700 p-6 rounded-lg text-center font-medium">
          ⚠️ Error: {error}
        </div>
      ) : documents.length === 0 ? (
        // Empty State
        <div className="bg-gray-100/50 border border-gray-200 p-16 rounded-lg text-center text-gray-500 font-medium">
          🗂️ No documents found in your knowledge base.
          <p className="mt-2 text-sm text-gray-400">
            Add documents through the main interface to see them here.
          </p>
        </div>
      ) : (
        // Table Rendering State
        <div className="bg-white shadow-md rounded-lg overflow-hidden border border-gray-100">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-100">
              <tr>
                <th
                  scope="col"
                  className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider"
                >
                  Document Title
                </th>
                <th
                  scope="col"
                  className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider"
                >
                  Total Vector Chunks
                </th>
                <th
                  scope="col"
                  className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider"
                >
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50 transition duration-100">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {doc.title}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-center text-gray-700 tabular-nums">
                    {doc.chunk_count.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => handleReindex(doc.title)}
                      className="text-gray-500 hover:text-gray-700 px-3 py-1 mr-2 rounded hover:bg-gray-100"
                    >
                      🔄 Re-index
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id, doc.title)}
                      className="text-red-500 hover:text-red-700 px-3 py-1 bg-red-50 hover:bg-red-100 rounded"
                    >
                      🗑️ Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="bg-gray-100 px-6 py-3 border-t border-gray-200 text-xs text-gray-500 font-medium">
            Total unique documents sitting in Qdrant for user: {documents.length}
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeBase;
