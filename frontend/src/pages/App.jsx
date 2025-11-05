import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function App() {
  const [file, setFile] = useState(null)
  const [extractionId, setExtractionId] = useState(null)

  const uploadMutation = useMutation({
    mutationFn: async (f) => {
      const form = new FormData()
      form.append('file', f)
      const { data } = await axios.post(`${API_BASE}/api/upload`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: (data) => setExtractionId(data.extraction_id),
  })

  const { data: result } = useQuery({
    queryKey: ['result', extractionId],
    queryFn: async () => (await axios.get(`${API_BASE}/api/result/${extractionId}`)).data,
    enabled: !!extractionId,
    refetchInterval: (q) => (q.state.data?.status === 'processing' ? 1500 : false),
  })

  const [editable, setEditable] = useState(null)

  React.useEffect(() => {
    if (result?.data && !editable) setEditable(result.data)
  }, [result])

  const verifyMutation = useMutation({
    mutationFn: async (payload) => (await axios.post(`${API_BASE}/api/verify`, payload)).data,
  })

  const submitMutation = useMutation({
    mutationFn: async (payload) => (await axios.post(`${API_BASE}/api/submit`, payload)).data,
  })

  return (
    <div style={{ maxWidth: 800, margin: '2rem auto', fontFamily: 'system-ui, sans-serif' }}>
      <h1>VisAI Assistant</h1>

      <section style={{ marginTop: 24, padding: 16, border: '1px solid #eee' }}>
        <h2>1) Upload</h2>
        <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => setFile(e.target.files?.[0])} />
        <button disabled={!file || uploadMutation.isPending} onClick={() => uploadMutation.mutate(file)} style={{ marginLeft: 12 }}>
          {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
        </button>
        {extractionId && <p>Extraction ID: {extractionId}</p>}
      </section>

      <section style={{ marginTop: 24, padding: 16, border: '1px solid #eee' }}>
        <h2>2) OCR Status</h2>
        {!extractionId && <p>Upload a document to start.</p>}
        {extractionId && <p>Status: {result?.status || 'waiting...'}</p>}
        {result?.raw_text && (
          <details>
            <summary>Raw text</summary>
            <pre style={{ whiteSpace: 'pre-wrap' }}>{result.raw_text}</pre>
          </details>
        )}
      </section>

      <section style={{ marginTop: 24, padding: 16, border: '1px solid #eee' }}>
        <h2>3) Autofill</h2>
        {!editable && <p>Awaiting extraction...</p>}
        {editable && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              verifyMutation.mutate(
                { data: editable },
                {
                  onSuccess: (res) => {
                    if (!res.valid) alert('Validation errors: ' + JSON.stringify(res.errors))
                    else alert('Looks good! You can submit.')
                  },
                }
              )
            }}
          >
            {['name', 'passport_number', 'dob', 'expiry_date'].map((k) => (
              <div key={k} style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontWeight: 600 }}>{k}</label>
                <input
                  value={editable[k] || ''}
                  onChange={(e) => setEditable((s) => ({ ...s, [k]: e.target.value }))}
                  style={{ width: '100%', padding: 8, border: '1px solid #ddd' }}
                />
              </div>
            ))}
            <button type="submit" disabled={verifyMutation.isPending}>
              {verifyMutation.isPending ? 'Verifying...' : 'Verify'}
            </button>
          </form>
        )}
      </section>

      <section style={{ marginTop: 24, padding: 16, border: '1px solid #eee' }}>
        <h2>4) Submit</h2>
        <button
          disabled={!extractionId || !editable || submitMutation.isPending}
          onClick={() => submitMutation.mutate({ extraction_id: extractionId, data: editable })}
        >
          {submitMutation.isPending ? 'Submitting...' : 'Submit Application'}
        </button>
        {submitMutation.data?.status === 'submitted' && <p>Submitted. ID: {submitMutation.data.extraction_id}</p>}
      </section>
    </div>
  )
}



