You are a senior backend engineer and audio processing expert.

I have a Python Flask server running on a VPS that downloads YouTube audio using yt-dlp and analyzes chords.

My project is NOT just chord detection — it must return chords synchronized with time (like Riffstation or Chordify).

---

GOAL:

Build a SIMPLE but production-ready Flask API that:

1. Downloads audio from YouTube
2. Analyzes chords WITH TIMESTAMPS
3. Returns time-synced chord progression
4. Protects the API (API key)
5. Prevents abuse (rate limiting)
6. Cleans up files

---

RESPONSE FORMAT (VERY IMPORTANT):

Return chords like:

[
{ "chord": "Am", "time": 0.0 },
{ "chord": "F", "time": 2.5 },
{ "chord": "G", "time": 5.1 }
]

Time must be in seconds (float).

---

REQUIREMENTS:

### 🎵 AUDIO PROCESSING

* Use librosa
* Load audio file
* Split audio into frames/windows
* Extract chroma features
* Detect chord per segment
* Smooth results (avoid too many rapid chord changes)
* Only output chord when it changes

---

### ⏱️ TIMING

* Track time per segment
* Ensure timestamps match real audio progression

---

### 🧠 CHORD QUALITY

* Avoid noisy/rare chords
* Prefer common chords (Am, F, G, C, Dm, E, etc.)
* Smooth transitions

---

### 🔐 SECURITY

* Require API key in header `x-api-key`
* Load key from environment variable
* Return 401 if invalid

---

### 🚫 RATE LIMIT

* Limit 1 request per IP every 5 seconds
* Return 429 if exceeded

---

### 🧹 CLEANUP

* Delete audio file after processing
* Ensure cleanup even if error happens

---

### ⚠️ ERROR HANDLING

* Always return JSON:
  {
  "success": false,
  "error": "message"
  }

---

### ⚡ PERFORMANCE

* Keep everything in ONE FILE
* No Redis, no queues, no microservices

---

### 📦 OUTPUT

Return FULL working Python Flask code including:

* yt-dlp download
* chord detection with timestamps
* API protection
* rate limiting
* cleanup

---

IMPORTANT:

* Do NOT overcomplicate
* Keep code readable and efficient
* Focus on correct timing + chord stability

---

My current function:

def analyze_audio(path):
# improve this
return [{"chord": "Am", "time": 0.0}]

---

Improve it to real chord + time detection.
