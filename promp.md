You are an expert in music theory and chord recognition.

My system is now mostly correct (~80%), but it misses important harmonic chords, especially the dominant chord (like E major in A minor songs).

Example:

* In A minor songs, E major (V chord) is often missing
* The system instead outputs Em or skips it entirely

Your task is to IMPROVE harmonic intelligence.

---

REQUIRED IMPROVEMENTS:

1. DOMINANT CHORD BOOST

* Detect key (e.g., A minor)
* Identify dominant chord (E major)
* Increase its score artificially (1.2–1.4x)

---

2. CONTEXT-AWARE CORRECTION

* If progression suggests dominant resolution:
  F → E → Am
  Dm → E → Am
* Insert or favor E chord even if confidence is medium

---

3. SECOND-BEST CHORD LOGIC

* Keep top 2 chord candidates
* If second candidate fits harmonic context better → use it

---

4. FIX MINOR/MAJOR CONFUSION

* If Em is detected but context suggests E → convert it

---

5. TEMPLATE ADJUSTMENT

* Reduce reliance on G# detection
* Emphasize root (E) and fifth (B)

---

6. MUSICAL RULES

In A minor:

* Strongly prefer:
  Am, Dm, F, G, C, E
* E should appear before resolving to Am

---

GOAL:

Recover missing harmonic chords (especially dominant chords)
Make progression closer to real songs (like Bailamos)

---

OUTPUT:

Provide code modifications focused on:

* scoring adjustment
* harmonic rules
* context-based correction

Focus on musical correctness, not just raw detection.
