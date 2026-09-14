import React, { useState } from "react";

export interface ProsePolishSettingsProps {
  onChange: (level: string) => void;
  initialLevel?: string;
}

export const ProsePolishSettings: React.FC<ProsePolishSettingsProps> = ({
  onChange,
  initialLevel = "標準",
}) => {
  const [selectedLevel, setSelectedLevel] = useState<string>(initialLevel);

  const handleLevelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const level = e.target.value;
    setSelectedLevel(level);
    onChange(level);
  };

  const levelOptions = [
    { value: "軽快", label: "軽快 (Web標準)", description: "軽快で読みやすい文体 - Web小説標準" },
    { value: "標準", label: "標準 (バランス)", description: "バランスの取れた標準的な文体" },
    { value: "文学的", label: "文学的 (ラノベ大賞風)", description: "文学的表現豊かな文体 - ライトノベル大賞レベル" },
  ];

  return (
    <div className="prose-polish-settings">
      <div className="form-group">
        <label className="form-label">文体推敲レベル</label>
        <select
          value={selectedLevel}
          onChange={handleLevelChange}
          className="form-select"
        >
          {levelOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <div className="form-description">
          {levelOptions.find((opt) => opt.value === selectedLevel)?.description}
        </div>
      </div>
    </div>
  );
};
