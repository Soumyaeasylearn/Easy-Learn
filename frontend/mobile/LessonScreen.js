// screens/LessonScreen.js
import React, { useState, useRef } from "react";
import {
  View, Text, TouchableOpacity, ScrollView, StyleSheet,
  ActivityIndicator, Alert,
} from "react-native";
import { Audio } from "expo-av";

const API = "https://your-render-app.onrender.com";  // ← update after deploy

export default function LessonScreen() {
  const [state,       setState]     = useState("idle");  // idle|recording|processing
  const [transcript,  setTranscript] = useState("");
  const [feedback,    setFeedback]   = useState(null);
  const recordingRef = useRef(null);
  const soundRef     = useRef(null);

  async function toggleRecording() {
    if (state === "idle") {
      await startRecording();
    } else if (state === "recording") {
      await stopAndTranscribe();
    }
  }

  async function startRecording() {
    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) { Alert.alert("Permission required", "Please allow microphone access."); return; }

      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      recordingRef.current = recording;
      setState("recording");
    } catch (e) {
      Alert.alert("Error", e.message);
    }
  }

  async function stopAndTranscribe() {
    setState("processing");
    setFeedback(null);
    const recording = recordingRef.current;
    if (!recording) return;

    await recording.stopAndUnloadAsync();
    const uri = recording.getURI();
    recordingRef.current = null;

    try {
      // 1. Upload audio for ASR
      const form = new FormData();
      form.append("file", { uri, type: "audio/m4a", name: "audio.m4a" });

      const asrRes  = await fetch(`${API}/asr/transcribe`, { method: "POST", body: form });
      const asrData = await asrRes.json();
      const text    = asrData.text || "";
      setTranscript(text);

      if (!text.trim()) {
        setFeedback({ encouragement: "Couldn't hear you — please try again!" });
        setState("idle");
        return;
      }

      // 2. Coach feedback
      const coachRes  = await fetch(`${API}/coach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "mobile-user", transcript: text }),
      });
      const coachData = await coachRes.json();
      setFeedback(coachData);

      // 3. Play TTS of correction
      if (coachData.correction) {
        const ttsRes = await fetch(`${API}/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: coachData.correction, format: "mp3" }),
        });
        const blob = await ttsRes.blob();
        // On RN, use temp file approach
        const { sound } = await Audio.Sound.createAsync({ uri: `${API}/tts?text=${encodeURIComponent(coachData.correction)}` });
        soundRef.current = sound;
        await sound.playAsync();
      }
    } catch (e) {
      Alert.alert("Error", "Could not connect to coaching server. Are you online?");
    } finally {
      setState("idle");
    }
  }

  const btnColor = { idle: "#7fff6e", recording: "#ff6e6e", processing: "#6b6b82" };
  const btnLabel = { idle: "🎙 Tap to Speak", recording: "⏹ Stop", processing: "⏳ Processing…" };

  return (
    <ScrollView style={s.screen} contentContainerStyle={s.content}>
      <Text style={s.heading}>Say anything in English</Text>
      <Text style={s.sub}>Tap the button and speak naturally.</Text>

      {/* Mic Button */}
      <TouchableOpacity
        style={[s.micBtn, { backgroundColor: btnColor[state] }]}
        onPress={toggleRecording}
        disabled={state === "processing"}
      >
        <Text style={s.micLabel}>{btnLabel[state]}</Text>
      </TouchableOpacity>

      {state === "processing" && (
        <ActivityIndicator size="large" color="#7fff6e" style={{ marginTop: 20 }} />
      )}

      {/* Transcript */}
      {transcript ? (
        <View style={s.card}>
          <Text style={s.cardLabel}>TRANSCRIPT</Text>
          <Text style={s.cardText}>{transcript}</Text>
        </View>
      ) : null}

      {/* Feedback */}
      {feedback ? (
        <View style={s.card}>
          {feedback.score != null && (
            <Text style={[s.score, { color: feedback.score >= 8 ? "#7fff6e" : feedback.score >= 5 ? "#ffe066" : "#ff6e6e" }]}>
              {feedback.score}/10
            </Text>
          )}
          {feedback.correction && (
            <>
              <Text style={s.cardLabel}>CORRECTION</Text>
              <Text style={[s.cardText, { color: "#7fff6e" }]}>{feedback.correction}</Text>
            </>
          )}
          {feedback.explanation ? (
            <>
              <Text style={[s.cardLabel, { marginTop: 12 }]}>EXPLANATION</Text>
              <Text style={s.cardText}>{feedback.explanation}</Text>
            </>
          ) : null}
          {feedback.encouragement ? (
            <View style={s.encourage}>
              <Text style={s.encourageText}>🌟 {feedback.encouragement}</Text>
            </View>
          ) : null}
        </View>
      ) : null}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  screen:   { flex: 1, backgroundColor: "#0a0a0f" },
  content:  { padding: 24, paddingBottom: 60, alignItems: "center" },
  heading:  { fontSize: 26, fontWeight: "800", color: "#e8e8f0", textAlign: "center", marginBottom: 8 },
  sub:      { color: "#6b6b82", fontSize: 14, marginBottom: 36, textAlign: "center" },
  micBtn:   { width: 180, height: 60, borderRadius: 999, justifyContent: "center",
               alignItems: "center", marginBottom: 32 },
  micLabel: { color: "#000", fontWeight: "700", fontSize: 16 },
  card:     { width: "100%", backgroundColor: "#13131a", borderRadius: 12,
               borderWidth: 1, borderColor: "#1e1e2e", padding: 16, marginTop: 16 },
  cardLabel:{ fontFamily: "monospace", fontSize: 11, color: "#6b6b82",
               textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 },
  cardText: { color: "#e8e8f0", fontSize: 15, lineHeight: 22 },
  score:    { fontSize: 42, fontWeight: "800", textAlign: "center", marginBottom: 12 },
  encourage:{ backgroundColor: "#1a1a0a", borderRadius: 8, padding: 12, marginTop: 12 },
  encourageText: { color: "#ffe066", fontSize: 14, lineHeight: 20 },
});
