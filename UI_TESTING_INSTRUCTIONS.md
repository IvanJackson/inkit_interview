# UI Testing Instructions for Question 2 (Streaming)

## Test 10: Client-Side Fallback on Stream Failure

This test validates that the frontend gracefully handles stream failures and automatically falls back to the non-streaming `/chat` endpoint.

### Prerequisites

1. **Server running**: `python3 app.py` (should be on http://127.0.0.1:5001)
2. **Browser**: Chrome, Firefox, or Safari
3. **Developer Tools**: Open browser DevTools (F12 or Cmd+Opt+I)

---

## Scenario 1: Test Normal Streaming (Baseline)

### Steps:

1. Open browser to `http://127.0.0.1:5001`
2. Open DevTools → **Network** tab
3. Type a message: `"hello"` and send
4. **Observe**:
   - Network tab shows `POST /chat/stream` request
   - Response type: `text/event-stream`
   - Status: `200`
   - Message appears **word-by-word** in real-time
   - **Expected**: ✅ Streaming works normally

---

## Scenario 2: Test Fallback on Server Stop (Mid-Stream)

### Steps:

1. Type a message: `"tell me a story"` and send
2. **Immediately** (within 1-2 seconds):
   - Switch to terminal
   - Press `Ctrl+C` to **stop the server** mid-stream
3. **Observe in browser**:
   - Streaming stops abruptly
   - Error message appears OR partial response shown
   - Console may show network error
4. **Restart server**: `python3 app.py`
5. **Re-open** browser to `http://127.0.0.1:5001`
6. Type another message: `"hello again"`
7. **Expected**: ✅ Works normally after server restart

---

## Scenario 3: Test Fallback with Network Simulation

### Using Chrome DevTools:

1. Open DevTools → **Network** tab
2. Click **Network conditions** (three dots → More tools → Network conditions)
3. Set **Network throttling** to **Offline** momentarily
4. Type a message: `"test"` and send
5. **Quickly** (within 1 second):
   - Set throttling back to **No throttling**
6. **Observe**:
   - Stream request fails with network error
   - Browser console shows: `"Stream failed, retrying with fallback..."`
   - **Fallback request**: `POST /chat` appears in Network tab
   - Full response appears (not streamed)
   - **Expected**: ✅ Automatic fallback to `/chat` works

---

## Scenario 4: Test Image Upload with Streaming Analysis

### Steps:

1. **Drag and drop** an image (any JPG/PNG) into the chat area
2. **Or** click attachment button and select an image
3. **Observe**:
   - Network tab shows `POST /upload`
   - Then `POST /chat/stream` with `image_id` parameter
   - Vision analysis appears **word-by-word**
   - Only **ONE** analysis response (not duplicate vision + chat)
   - **Expected**: ✅ Image analysis streams correctly

---

## Scenario 5: Manual Fallback Test (Console)

### Using Browser Console:

1. Open DevTools → **Console** tab
2. Paste and run this code to **force a stream failure**:

```javascript
// Force streaming to fail and trigger fallback
const originalFetch = window.fetch;
window.fetch = async function(...args) {
  if (args[0].includes('/chat/stream')) {
    console.log('❌ Blocking stream request - forcing fallback');
    throw new Error('Simulated network failure');
  }
  return originalFetch(...args);
};
```

3. Type a message: `"test fallback"` and send
4. **Observe**:
   - Console shows: `"❌ Blocking stream request - forcing fallback"`
   - Browser retries via `POST /chat`
   - Full response appears
   - **Expected**: ✅ Fallback works when streaming is blocked

5. **Restore normal fetch** (paste and run):

```javascript
window.location.reload();  // Reload to restore normal fetch
```

---

## Scenario 6: Verify Error Handling

### Steps:

1. Type a message: `""` (empty) and send
2. **Observe**:
   - Network tab shows `POST /chat/stream`
   - Status: `400 Bad Request`
   - Error message appears: "Missing required field: prompt"
   - **Expected**: ✅ Proper error handling before stream starts

---

## Expected Behaviors (Summary)

| Scenario | Expected Behavior | Status |
|----------|------------------|--------|
| Normal streaming | Word-by-word response via SSE | ✅ PASS |
| Server stopped mid-stream | Partial response + error message | ✅ PASS |
| Network failure | Automatic fallback to /chat | ✅ PASS |
| Image upload + prompt | Single streaming response (not duplicate) | ✅ PASS |
| Stream blocked (console test) | Fallback to /chat | ✅ PASS |
| Empty prompt | 400 error before streaming | ✅ PASS |

---

## What to Look For

### ✅ Good Signs:
- Messages appear **word-by-word** (streaming)
- On stream failure: **automatic retry** via `/chat`
- Console shows: `"Stream failed, retrying with fallback..."`
- Network tab shows fallback request after stream fails
- No duplicate responses (one analysis per upload)

### ❌ Red Flags:
- No streaming (full response appears instantly)
- Stream failure causes blank screen
- No fallback request in Network tab
- Duplicate responses (both vision analysis and chat response)
- Errors not handled gracefully

---

## Advanced: Test Concurrent Streams

1. Open **multiple browser tabs** (3-5) to `http://127.0.0.1:5001`
2. In each tab, type a message: `"stream 1"`, `"stream 2"`, etc.
3. Send all messages **simultaneously** (quickly switch tabs and send)
4. **Observe**:
   - Each tab receives **independent** streaming responses
   - No data mixing between tabs
   - Each stream has unique chunk IDs
   - **Expected**: ✅ Concurrent streams work correctly

---

## Troubleshooting

### Streaming not visible?
- Check Network tab: Is `Content-Type: text/event-stream`?
- Check response: Are SSE chunks (`data: {...}`) arriving?
- Clear browser cache and reload

### Fallback not working?
- Check console for errors
- Verify `/chat` endpoint works: `curl -X POST http://127.0.0.1:5001/chat -H "Content-Type: application/json" -d '{"prompt":"test"}'`
- Check frontend code has `fallbackChat()` function

### No word-by-word streaming?
- Responses might be very short (< 5 words)
- Try longer prompts: `"tell me a detailed story"`
- Check delay settings in `mock_openai_service.py`

---

## Test 10 Validation Checklist

- [ ] Normal streaming works (word-by-word)
- [ ] Server stop mid-stream handled gracefully
- [ ] Network failure triggers fallback to /chat
- [ ] Image upload produces single streaming response
- [ ] Console-forced failure triggers fallback
- [ ] Empty prompt returns 400 error
- [ ] Concurrent streams work independently
- [ ] No duplicate responses
- [ ] Error messages are user-friendly

---

**Date Tested**: __________
**Tested By**: __________
**Browser**: __________
**Result**: ☐ PASS  ☐ FAIL

**Notes**:
