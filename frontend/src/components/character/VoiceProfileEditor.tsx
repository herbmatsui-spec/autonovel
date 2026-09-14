import React, { useState } from 'react';

interface Props {
  onSave: (profile: any) => void;
}

export const VoiceProfileEditor: React.FC<Props> = ({ onSave }) => {
  const [profile, setProfile] = useState({
    character_name: '',
    first_person: '',
    second_person: '',
    endings: '',
  });

  const presets = {
    tsundere: { first_person: '私', second_person: 'あんた', endings: '〜じゃない,〜でしょ' },
    ojousama: { first_person: 'わたくし', second_person: '貴方様', endings: '〜ですわ,〜ましてよ' },
  };

  const applyPreset = (key: keyof typeof presets) => {
    setProfile(prev => ({ ...prev, ...presets[key] }));
  };

  return (
    <div className="p-4 border rounded">
      <h2 className="text-lg font-bold mb-2">ボイスプロファイル編集</h2>
      <div className="flex gap-2 mb-4">
        {Object.keys(presets).map(key => (
          <button key={key} onClick={() => applyPreset(key as any)} className="px-2 py-1 bg-blue-500 text-white rounded">
            {key}
          </button>
        ))}
      </div>
      <input 
        value={profile.character_name} 
        onChange={e => setProfile({...profile, character_name: e.target.value})}
        placeholder="キャラクター名"
        className="w-full mb-2 p-1 border"
      />
      <input 
        value={profile.first_person} 
        onChange={e => setProfile({...profile, first_person: e.target.value})}
        placeholder="一人称 (カンマ区切り)"
        className="w-full mb-2 p-1 border"
      />
      <button onClick={() => onSave(profile)} className="px-4 py-2 bg-green-500 text-white rounded">
        保存
      </button>
    </div>
  );
};
