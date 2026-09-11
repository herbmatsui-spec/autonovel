import React, { useRef, useState, useEffect } from "react";
import "./AudioPlayer.css";

interface AudioPlayerProps {
  src: string;
  title?: string;
  duration?: number;
  onEnded?: () => void;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  src,
  title = "章朗読音声",
  duration: initialDuration = 0,
  onEnded,
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(initialDuration);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [volume, setVolume] = useState(1.0);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoadedMetadata = () => {
      if (audio.duration && !isNaN(audio.duration)) {
        setDuration(audio.duration);
      }
    };
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const handleEnded = () => {
      setIsPlaying(false);
      if (onEnded) onEnded();
    };

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("loadedmetadata", onLoadedMetadata);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    audio.addEventListener("ended", handleEnded);

    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("loadedmetadata", onLoadedMetadata);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
      audio.removeEventListener("ended", handleEnded);
    };
  }, [onEnded]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch((e) => console.error("Playback failed:", e));
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const targetTime = parseFloat(e.target.value);
    setCurrentTime(targetTime);
    if (audioRef.current) {
      audioRef.current.currentTime = targetTime;
    }
  };

  const handleRateChange = (rate: number) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const vol = parseFloat(e.target.value);
    setVolume(vol);
    if (audioRef.current) {
      audioRef.current.volume = vol;
    }
  };

  const formatTime = (secs: number) => {
    if (isNaN(secs)) return "00:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="audio-player-container">
      <audio ref={audioRef} src={src} preload="metadata" />
      <div className="audio-player-header">
        <span className="audio-player-title">🔊 {title}</span>
        <div className="audio-player-speed-controls">
          {[1.0, 1.25, 1.5].map((rate) => (
            <button
              key={rate}
              type="button"
              className={`audio-speed-btn ${playbackRate === rate ? "active" : ""}`}
              onClick={() => handleRateChange(rate)}
            >
              {rate}x
            </button>
          ))}
        </div>
      </div>

      <div className="audio-player-main-controls">
        <button
          type="button"
          className="audio-play-toggle-btn"
          onClick={togglePlay}
          aria-label={isPlaying ? "一時停止" : "再生"}
        >
          {isPlaying ? "⏸️" : "▶️"}
        </button>

        <span className="audio-time-label">{formatTime(currentTime)}</span>

        <input
          type="range"
          className="audio-seek-slider"
          min={0}
          max={duration || 100}
          step={0.1}
          value={currentTime}
          onChange={handleSeek}
        />

        <span className="audio-time-label">{formatTime(duration)}</span>

        <div className="audio-volume-wrapper">
          <span className="audio-volume-icon">🔈</span>
          <input
            type="range"
            className="audio-volume-slider"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={handleVolumeChange}
            aria-label="音量"
          />
        </div>
      </div>
    </div>
  );
};
