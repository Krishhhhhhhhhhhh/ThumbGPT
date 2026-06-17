import { useState } from 'react'
import { uploadHeadshot, createJob, subscribeToJob } from './api'
import './App.css'

function App() {
  const [headshotFile, setHeadshotFile] = useState(null)
  const [headshotUrl, setHeadshotUrl] = useState('')
  const [headshotPreview, setHeadshotPreview] = useState('')
  const [prompt, setPrompt] = useState('')
  const [numThumbnails, setNumThumbnails] = useState(1)
  const [loading, setLoading] = useState(false)
  const [thumbnails, setThumbnails] = useState([])
  const [jobId, setJobId] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const handleHeadshotChange = (e) => {
    const file = e.target.files[0]
    if (file) {
      setHeadshotFile(file)
      const reader = new FileReader()
      reader.onload = (event) => {
        setHeadshotPreview(event.target.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleUploadHeadshot = async () => {
    if (!headshotFile) {
      setError('Please select a headshot image')
      return
    }
    try {
      setLoading(true)
      setError('')
      const result = await uploadHeadshot(headshotFile)
      setHeadshotUrl(result.url)
      setSuccess('Headshot uploaded successfully!')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError('Failed to upload headshot: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateJob = async () => {
    if (!headshotUrl) {
      setError('Please upload a headshot first')
      return
    }
    if (!prompt.trim()) {
      setError('Please enter a prompt')
      return
    }
    try {
      setLoading(true)
      setError('')
      setThumbnails([])
      const result = await createJob({
        prompt: prompt.trim(),
        numThumbnails: parseInt(numThumbnails),
        headshotUrl: headshotUrl,
      })
      setJobId(result.job_id)
      setSuccess('Job created! Generating thumbnails...')
      subscribeToJobUpdates(result.job_id)
    } catch (err) {
      setError('Failed to create job: ' + err.message)
      setLoading(false)
    }
  }

  const subscribeToJobUpdates = (id) => {
    const eventSource = subscribeToJob(id, {
      onThumbnailReady: (data) => {
        setThumbnails((prev) => [
          ...prev,
          {
            id: data.thumbnail_id,
            style: data.style_name,
            url: data.image_kit_url,
            variants: data.variants,
            status: 'ready',
          },
        ])
      },
      onThumbnailFailed: (data) => {
        setThumbnails((prev) => [
          ...prev,
          {
            id: data.thumbnail_id,
            style: data.style_name,
            error: data.error,
            status: 'failed',
          },
        ])
      },
      onJobComplete: (data) => {
        setSuccess('All thumbnails generated!')
        setLoading(false)
        eventSource.close()
      },
      onError: (err) => {
        setError('Streaming error: ' + JSON.stringify(err))
        setLoading(false)
        eventSource.close()
      },
    })
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🎬 Thumbnail Generator</h1>
        <p>Generate AI-powered video thumbnails using Grok</p>
      </header>

      <main className="container">
        {/* Error Alert */}
        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-success">{success}</div>}

        {/* Upload Section */}
        <section className="section">
          <h2>Step 1: Upload Your Headshot</h2>
          <div className="upload-area">
            <input
              type="file"
              id="headshot-input"
              accept="image/*"
              onChange={handleHeadshotChange}
              disabled={loading}
            />
            <label htmlFor="headshot-input" className="upload-label">
              {headshotPreview ? (
                <img src={headshotPreview} alt="Preview" className="preview-image" />
              ) : (
                <div className="upload-placeholder">
                  <span>📸 Click to upload or drag & drop</span>
                  <small>PNG, JPG up to 10MB</small>
                </div>
              )}
            </label>
            <button
              onClick={handleUploadHeadshot}
              disabled={!headshotFile || loading || !!headshotUrl}
              className="btn btn-primary"
            >
              {loading ? 'Uploading...' : headshotUrl ? '✓ Uploaded' : 'Upload Headshot'}
            </button>
          </div>
          {headshotUrl && <p className="success-text">✓ Headshot ready for thumbnail generation</p>}
        </section>

        {/* Form Section */}
        {headshotUrl && (
          <section className="section">
            <h2>Step 2: Create Your Thumbnails</h2>
            <div className="form-group">
              <label htmlFor="prompt">Prompt</label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what you want in the thumbnail..."
                rows="4"
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="num-thumbnails">Number of Thumbnails</label>
              <select
                id="num-thumbnails"
                value={numThumbnails}
                onChange={(e) => setNumThumbnails(e.target.value)}
                disabled={loading}
              >
                <option value="1">1 thumbnail</option>
                <option value="2">2 thumbnails</option>
                <option value="3">3 thumbnails</option>
              </select>
            </div>

            <button
              onClick={handleCreateJob}
              disabled={loading || !prompt.trim()}
              className="btn btn-primary btn-large"
            >
              {loading ? '⏳ Generating...' : '🚀 Generate Thumbnails'}
            </button>
          </section>
        )}

        {/* Results Section */}
        {jobId && (
          <section className="section">
            <h2>Step 3: Your Generated Thumbnails</h2>
            {loading && thumbnails.length === 0 && (
              <div className="loading-state">
                <div className="spinner"></div>
                <p>Generating thumbnails...</p>
              </div>
            )}

            {thumbnails.length > 0 && (
              <div className="thumbnails-grid">
                {thumbnails.map((thumb) => (
                  <div key={thumb.id} className="thumbnail-card">
                    {thumb.status === 'ready' ? (
                      <>
                        <img src={thumb.url} alt={thumb.style} className="thumbnail-image" />
                        <h3>{thumb.style}</h3>
                        {thumb.variants && (
                          <div className="variants">
                            <p><strong>Variants:</strong></p>
                            <a href={thumb.variants.youtube} target="_blank" rel="noreferrer">
                              YouTube (1280x720)
                            </a>
                            <a href={thumb.variants.shorts} target="_blank" rel="noreferrer">
                              Shorts (1080x1920)
                            </a>
                            <a href={thumb.variants.square} target="_blank" rel="noreferrer">
                              Square (1080x1080)
                            </a>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="error-state">
                        <p>❌ Failed</p>
                        <small>{thumb.error}</small>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
            'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
            sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          min-height: 100vh;
        }

        .app {
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        .header {
          text-align: center;
          color: white;
          padding: 40px 20px;
          background: rgba(0, 0, 0, 0.2);
        }

        .header h1 {
          font-size: 2.5em;
          margin-bottom: 10px;
        }

        .header p {
          font-size: 1.1em;
          opacity: 0.9;
        }

        .container {
          max-width: 900px;
          margin: 0 auto;
          padding: 40px 20px;
        }

        .section {
          background: white;
          border-radius: 12px;
          padding: 30px;
          margin-bottom: 30px;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }

        .section h2 {
          color: #333;
          margin-bottom: 20px;
          font-size: 1.5em;
        }

        .alert {
          padding: 15px 20px;
          border-radius: 8px;
          margin-bottom: 20px;
          font-weight: 500;
        }

        .alert-error {
          background: #fee;
          color: #c33;
          border: 1px solid #fcc;
        }

        .alert-success {
          background: #efe;
          color: #3c3;
          border: 1px solid #cfc;
        }

        .upload-area {
          display: flex;
          flex-direction: column;
          gap: 15px;
        }

        input[type='file'] {
          display: none;
        }

        .upload-label {
          cursor: pointer;
          border: 2px dashed #667eea;
          border-radius: 8px;
          padding: 40px;
          text-align: center;
          transition: all 0.3s;
          background: #f8f9ff;
        }

        .upload-label:hover {
          border-color: #764ba2;
          background: #f0f2ff;
        }

        .upload-placeholder {
          display: flex;
          flex-direction: column;
          gap: 8px;
          color: #667eea;
        }

        .upload-placeholder span {
          font-weight: 600;
          font-size: 1.1em;
        }

        .upload-placeholder small {
          color: #999;
        }

        .preview-image {
          max-width: 200px;
          max-height: 200px;
          border-radius: 8px;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .form-group label {
          display: block;
          margin-bottom: 8px;
          font-weight: 600;
          color: #333;
        }

        .form-group textarea,
        .form-group select {
          width: 100%;
          padding: 12px;
          border: 1px solid #ddd;
          border-radius: 8px;
          font-size: 1em;
          font-family: inherit;
          resize: vertical;
        }

        .form-group textarea:focus,
        .form-group select:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .btn {
          padding: 12px 24px;
          border: none;
          border-radius: 8px;
          font-size: 1em;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
        }

        .btn-primary {
          background: #667eea;
          color: white;
        }

        .btn-primary:hover:not(:disabled) {
          background: #764ba2;
          transform: translateY(-2px);
          box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
        }

        .btn-primary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .btn-large {
          width: 100%;
          padding: 15px;
          font-size: 1.1em;
        }

        .success-text {
          color: #3c3;
          font-weight: 600;
          margin-top: 10px;
        }

        .loading-state {
          text-align: center;
          padding: 40px;
        }

        .spinner {
          border: 4px solid #f3f3f3;
          border-top: 4px solid #667eea;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          animation: spin 1s linear infinite;
          margin: 0 auto 20px;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .thumbnails-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 20px;
        }

        .thumbnail-card {
          border: 1px solid #eee;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          transition: transform 0.3s;
        }

        .thumbnail-card:hover {
          transform: translateY(-5px);
          box-shadow: 0 5px 20px rgba(0, 0, 0, 0.15);
        }

        .thumbnail-image {
          width: 100%;
          height: 200px;
          object-fit: cover;
        }

        .thumbnail-card h3 {
          padding: 15px;
          color: #333;
          text-transform: capitalize;
          border-bottom: 1px solid #eee;
        }

        .variants {
          padding: 15px;
        }

        .variants p {
          margin-bottom: 10px;
          font-size: 0.9em;
          color: #666;
        }

        .variants a {
          display: block;
          padding: 8px 0;
          color: #667eea;
          text-decoration: none;
          font-size: 0.85em;
          border-bottom: 1px solid #f0f0f0;
          transition: color 0.3s;
        }

        .variants a:hover {
          color: #764ba2;
        }

        .variants a:last-child {
          border-bottom: none;
        }

        .error-state {
          padding: 30px;
          text-align: center;
          color: #c33;
        }

        .error-state p {
          font-size: 1.5em;
          margin-bottom: 10px;
        }

        @media (max-width: 768px) {
          .header h1 {
            font-size: 1.8em;
          }

          .section {
            padding: 20px;
          }

          .thumbnails-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  )
}

export default App
