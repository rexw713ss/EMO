import React, { useState, useEffect } from 'react';

// 定義 4 種情緒的視覺風格參數
const EMOTION_CONFIGS = {
  CALM: {
    label: '平靜',
    bgColor: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
    elementColor: '#70a1ff',
    pulseDuration: '4s',
  },
  JOY: {
    label: '愉悅',
    bgColor: 'linear-gradient(135deg, #ff7e5f 0%, #feb47b 100%)',
    elementColor: '#ffeaa7',
    pulseDuration: '2s', 
  },
  ANXIOUS: {
    label: '緊張',
    bgColor: 'linear-gradient(135deg, #eb3b5a 0%, #fa8231 100%)',
    elementColor: '#ff4d4d',
    pulseDuration: '0.8s',
  },
  DEPRESSED: {
    label: '低落',
    bgColor: 'linear-gradient(135deg, #2d1436 0%, #4b1248 100%)',
    elementColor: '#a55eea',
    pulseDuration: '6s',
  }
};

const EMOTION_KEYS = Object.keys(EMOTION_CONFIGS);

export default function EmotionVisualDisplay() {
  const [currentEmotion, setCurrentEmotion] = useState('CALM');
  const [safeMode, setSafeMode] = useState(false);
  const [isAutoPlay, setIsAutoPlay] = useState(true);

  // 純前端定時自動輪播邏輯
  useEffect(() => {
    if (!isAutoPlay) return; // 如果關閉自動輪播，就停留在當前情緒

    const interval = setInterval(() => {
      setCurrentEmotion((prev) => {
        const currentIndex = EMOTION_KEYS.indexOf(prev);
        const nextIndex = (currentIndex + 1) % EMOTION_KEYS.length;
        return EMOTION_KEYS[nextIndex];
      });
    }, 4000); // 每 4 秒自動切換下一個情緒

    return () => clearInterval(interval);
  }, [isAutoPlay]);

  const config = EMOTION_CONFIGS[currentEmotion];
  const activePulseDuration = safeMode ? '4s' : config.pulseDuration;
  const activeOpacity = safeMode ? '0.6' : '1.0';

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        margin: 0,
        padding: 0,
        background: config.bgColor,
        transition: 'background 2.5s ease-in-out, filter 1.5s ease',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#ffffff',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        overflow: 'hidden',
        position: 'fixed',
        top: 0,
        left: 0,
        filter: safeMode ? 'brightness(80%) contrast(85%)' : 'none'
      }}
    >
      {/* 呼吸動態視覺球 */}
      <div
        style={{
          width: '280px',
          height: '280px',
          borderRadius: '50%',
          backgroundColor: config.elementColor,
          opacity: activeOpacity,
          boxShadow: `0 0 90px ${config.elementColor}`,
          animation: `pulseAnimation ${activePulseDuration} infinite ease-in-out`,
          transition: 'background-color 2.5s ease-in-out, box-shadow 2.5s ease-in-out'
        }}
      />

      {/* 控制卡片面板 */}
      <div
        style={{
          position: 'absolute',
          bottom: '30px',
          backgroundColor: 'rgba(0, 0, 0, 0.55)',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          padding: '24px 32px',
          borderRadius: '20px',
          textAlign: 'center',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          maxWidth: '90vw',
          width: '380px'
        }}
      >
        <h2 style={{ margin: '0 0 6px 0', fontSize: '1.6rem', fontWeight: '600' }}>
          當前情緒：{config.label}
        </h2>
        <p style={{ margin: '0 0 16px 0', fontSize: '0.9rem', opacity: 0.85 }}>
          {config.description}
        </p>

        {/* 手動選擇情緒按鈕區 */}
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginBottom: '16px' }}>
          {EMOTION_KEYS.map((key) => (
            <button
              key={key}
              onClick={() => {
                setCurrentEmotion(key);
                setIsAutoPlay(false); // 點擊手動切換時，自動暫停輪播
              }}
              style={{
                padding: '6px 12px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: currentEmotion === key ? '#ffffff' : 'rgba(255, 255, 255, 0.2)',
                color: currentEmotion === key ? '#000000' : '#ffffff',
                fontWeight: currentEmotion === key ? 'bold' : 'normal',
                cursor: 'pointer',
                fontSize: '0.85rem',
                transition: 'all 0.3s ease'
              }}
            >
              {EMOTION_CONFIGS[key].label}
            </button>
          ))}
        </div>

        {/* 開關選項 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'center' }}>
          <label style={{ cursor: 'pointer', fontSize: '0.85rem', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={isAutoPlay}
              onChange={(e) => setIsAutoPlay(e.target.checked)}
              style={{ marginRight: '6px', cursor: 'pointer' }}
            />
            🔄 自動播放輪播 (每 4 秒切換)
          </label>

          <label style={{ cursor: 'pointer', fontSize: '0.85rem', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={safeMode}
              onChange={(e) => setSafeMode(e.target.checked)}
              style={{ marginRight: '6px', cursor: 'pointer' }}
            />
            🛡️ 開啟視覺安全模式 (防閃爍與疲勞)
          </label>
        </div>
      </div>

      {/* 動畫樣式注入 */}
      <style>{`
        @keyframes pulseAnimation {
          0% { transform: scale(0.85); }
          50% { transform: scale(1.15); }
          100% { transform: scale(0.85); }
        }
      `}</style>
    </div>
  );
}