import React from 'react';
import { EMOTION_CONFIGS } from '../constants/emotionConfig';

export default function EmotionControlPanel({
  currentEmotion = 'UNKNOWN',
  onSelectEmotion
}) {
  const config = (EMOTION_CONFIGS && EMOTION_CONFIGS[currentEmotion]) 
    || (EMOTION_CONFIGS && EMOTION_CONFIGS.UNKNOWN) 
    || { label: '未知', description: '當前無法明確判定情緒' };

  // 按鈕清單（對應的物件 key 與中文顯示名稱）
  const buttons = [
    { key: 'CALM', label: '平靜' },
    { key: 'JOY', label: '愉悅' },
    { key: 'ANXIOUS', label: '緊張' },
    { key: 'DEPRESSED', label: '低落' },
    { key: 'UNKNOWN', label: '未知' }
  ];

  return (
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
        width: '420px'
      }}
    >
      <h2 style={{ margin: '0 0 6px 0', fontSize: '1.6rem', fontWeight: '600' }}>
        目前情緒：{config?.label || '未知'}
      </h2>
      <p style={{ margin: '0 0 16px 0', fontSize: '0.9rem', opacity: 0.85 }}>
        {config?.description || ''}
      </p>

      {/* 手動選擇情緒按鈕區 */}
      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap' }}>
        {buttons.map((btn) => (
          <button
            key={btn.key}
            onClick={() => onSelectEmotion && onSelectEmotion(btn.key)}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: currentEmotion === btn.key ? '#ffffff' : 'rgba(255, 255, 255, 0.2)',
              color: currentEmotion === btn.key ? '#000000' : '#ffffff',
              fontWeight: currentEmotion === btn.key ? 'bold' : 'normal',
              cursor: 'pointer',
              fontSize: '0.85rem',
              transition: 'all 0.3s ease'
            }}
          >
            {btn.label}
          </button>
        ))}
      </div>
    </div>
  );
}