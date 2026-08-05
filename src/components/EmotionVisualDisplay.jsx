import React from 'react';

export default function EmotionVisualDisplay({
  emotionData,
  children
}) {
  const bgColor = emotionData?.bgColor || 'linear-gradient(135deg, #3a3d40 0%, #181719 100%)';
  const elementColor = emotionData?.elementColor || '#a0a0a0';
  const duration = emotionData?.pulseDuration || '5s';

  return (
    <div
      style={{
        position: 'relative',
        width: '100vw',
        height: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        background: bgColor,
        transition: 'background 1.2s ease-in-out',
        overflow: 'hidden',
        color: '#ffffff',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}
    >
      {/* 微微融入背景的模糊微光球 */}
      <div
        style={{
          position: 'absolute',
          width: '380px',
          height: '380px',
          borderRadius: '50%',
          backgroundColor: elementColor,
          filter: 'blur(50px)',
          boxShadow: `0 0 100px ${elementColor}`,
          opacity: 0.35,
          mixBlendMode: 'screen',
          animation: `subtlePulse ${duration} infinite ease-in-out`,
          transition: 'all 1.2s ease-in-out',
          pointerEvents: 'none'
        }}
      />

      <style>
        {`
          @keyframes subtlePulse {
            0% {
              transform: scale(0.85);
              opacity: 0.25;
            }
            50% {
              transform: scale(1.15);
              opacity: 0.45;
            }
            100% {
              transform: scale(0.85);
              opacity: 0.25;
            }
          }
        `}
      </style>

      {/* 控制面板 */}
      {children}
    </div>
  );
}