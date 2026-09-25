// AutoNovel かんたんモード デモ モックデータ

// 企画ガチャ結果データ
const GACHA_RESULTS = {
  royal: [
    {
      plan_id: "royal_001",
      plan_type: "royal",
      title: "聖剣選ばれし者",
      logline: "古代の聖剣を引き出した少年が、王国を救うために旅立つ王道ファンタジー",
      protagonist_summary: "アルト - 熱血・仲間思い・冷静な判断力を持つ辺境の村の少年",
      charm_point: "王道展開ながらも、仲間との絆と成長ストーリーが心に響く"
    },
    {
      plan_id: "royal_002",
      plan_type: "royal",
      title: "魔法学園の優等生",
      logline: "魔法が苦手な少女が、努力と友情でトップを目指す学園ファンタジー",
      protagonist_summary: "リナ - 努力家だが魔法の才能に恵まれない少女。友達との絆で成長する",
      charm_point: "努力と友情をテーマにした心温まるストーリーと、丁寧なキャラクター描写"
    }
  ],
  curveball: [
    {
      plan_id: "curveball_001",
      plan_type: "curveball",
      title: "転生したらスライムだった件について",
      logline: "最弱モンスターに転生した主人公が、知恵と勇気で逆境を乗り越えていく異世界転生コメディ",
      protagonist_summary: "リムル - 前世の知識を活かし、スライムという不利な状況を強みに変える",
      charm_point: "転生ものの常識を覆す斬新な設定と、コミカルながらも熱い展開"
    },
    {
      plan_id: "curveball_002",
      plan_type: "curveball",
      title: "悪役令嬢は hidden boss を目指す",
      logline: "ゲームの中の悪役令嬢に転生した主人公が、バッドエンドを避けるために隠しボスを目指す",
      protagonist_summary: "アリシア - ゲーム知識を活かして生存を賭けた戦略を立てる転生者",
      charm_point: "ゲーム知識を活かした戦略劇と、予想外のキャラクター発展が面白い"
    }
  ],
  dark: [
    {
      plan_id: "dark_001",
      plan_type: "dark",
      title: "暗黒騎士の復讐譚",
      logline: "王族を殺された騎士が、闇の力を手に入れて復讐を誓うダークファンタジー",
      protagonist_summary: "カイン - 正義感が強かった元騎士。復讐のために闇に堕ちていく tragic hero",
      charm_point: "復讐劇の重厚さと、主人公の心理描写の深さが魅力"
    },
    {
      plan_id: "dark_002",
      plan_type: "dark",
      title: "血塗られた王冠の継承者",
      logline: "王位継承権を奪われた王女が、暗殺と陰謀の渦中で真の力を覚醒させる",
      protagonist_summary: "イザベラ - 純粋だった王女。復讐のために毒と陰謀の世界に身を投じる",
      charm_point: "ダークな宮廷劇と、主人公の心理的変化の描写が見事"
    }
  ]
};

// 逆算プロットビルダー用サンプルデータ
const SAMPLE_PLOT_DATA = {
  episodes: [
    {
      ep_num: 1,
      title: "第1話 運命の出会い",
      one_line_summary: "迷宮の最深部で古代の魔剣を引き出したアルトは、謎の少女と出会う",
      is_catharsis: false
    },
    {
      ep_num: 2,
      title: "第2話 試練の洞窟",
      one_line_summary: "二人は試練の洞窟を探索し、そこで最初の強敵と遭遇する",
      is_catharsis: false
    },
    {
      ep_num: 3,
      title: "第3話 王都への道",
      one_line_summary: "迷宮を脱出したアルトたちは、王都を目指して旅を始める",
      is_catharsis: false
    },
    {
      ep_num: 4,
      title: "第4話 影の使者",
      one_line_summary: "王都手前で、闇の組織の使者と遭遇し、本当の脅威が明らかになる",
      is_catharsis: true
    }
  ]
};

// 生成本文サンプル
const SAMPLE_GENERATED_TEXT = `薄暗い迷宮の最深部、少年アルトは封印されし古代の魔剣を抜いた。
その刃から放たれる青白い光が、壁に刻まれた古代の文字を照らす。

「 finalmente… 」アルトはつぶやき、汗で濡れた額を拭った。
三日間の探索の末、ついに伝説の「光の剣」を見つけ出したのだ。

突然、背後に気配を感じてアルトは剣を構える。
「誰だ！出てこい！」彼の声が迷宮に響く。

影から現れたのは、銀白色の長髪をした少女だった。
白いローブに身を包み、片手には不思議な光るクリスタルを持っている。

「あなたが…選ばれし者？」少女の声は澄んでいて、どこか echoes しているように聞える。
「私はリナ。この迷宮の守護者。そして…あなたの旅の最初の試練だ」`;

const SAMPLE_SUGGESTIONS = [
  "リナとともに迷宮の上層部を探索し、最初の街へと向かう",
  "アルトの過去が明らかになり、彼がなぜこの剣を選ばれたのかが判明する",
  "闇の組織の真の目的が明らかになり、二人は予期せぬ同盟を結ぶ"
];

// 現在のデモ状態を管理する
const DEMO_STATE = {
  currentStep: 1,
  selectedGachaPlan: null,
  character: {
    name: "",
    personality: "",
    ability: "",
    genre: ""
  },
  openingText: "",
  generatedText: "",
  suggestions: [],
  isGenerating: false,
  isStreaming: false,
  tutorialMode: false
};

// ユーティリティ関数
const Utils = {
  // ランダムな項目を選択
  randomItem: (array) => array[Math.floor(Math.random() * array.length)],
  
  // 遅延（ミリ秒）
  delay: (ms) => new Promise(resolve => setTimeout(resolve, ms)),
  
  // テキストをタイピングエフェクトで表示
  typeWriter: (element, text, speed = 50) => {
    let i = 0;
    element.textContent = '';
    return new Promise((resolve) => {
      const type = () => {
        if (i < text.length) {
          element.textContent += text.charAt(i);
          i++;
          setTimeout(type, speed);
        } else {
          resolve();
        }
      };
      type();
    });
  },
  
  // モーダル表示
  showModal: (title, content) => {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    
    const modal = document.createElement('div');
    modal.className = 'modal';
    
    modal.innerHTML = `
      <button class="modal-close">&times;</button>
      <h2>${title}</h2>
      <div class="modal-content">${content}</div>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    modal.querySelector('.modal-close').addEventListener('click', () => {
      document.body.removeChild(overlay);
    });
    
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        document.body.removeChild(overlay);
      }
    });
  },
  
  // トースト表示
  showToast: (message, type = 'info', duration = 3000) => {
    const container = document.querySelector('.toast-container') || 
                    (() => {
                      const c = document.createElement('div');
                      c.className = 'toast-container';
                      document.body.appendChild(c);
                      return c;
                    })();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <div class="toast-content">${message}</div>
      <div class="toast-progress"><div></div></div>
    `;
    
    container.appendChild(toast);
    
    // アニメーション開始
    requestAnimationFrame(() => {
      toast.querySelector('.toast-progress div').style.width = '100%';
    });
    
    // 指定時間後に削除
    setTimeout(() => {
      toast.remove();
      if (container.children.length === 0) {
        container.remove();
      }
    }, duration);
  }
};