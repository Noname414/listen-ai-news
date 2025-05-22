// 讀取 JSONL 檔案
async function loadArticles() {
  try {
    const response = await fetch("news.jsonl");
    const text = await response.text();
    // 將 JSONL 文字分割成行並解析每一行，直接反轉順序
    return text
      .trim()
      .split("\n")
      .map((line) => JSON.parse(line))
      .reverse(); // 直接反轉陣列順序，最新的文章會在最前面
  } catch (error) {
    console.error("載入文章失敗:", error);
    return [];
  }
}

// 建立音訊播放列表
function createAudioList(articles) {
  return articles.map((article) => {
    const authors = Array.isArray(article.authors)
      ? article.authors.join("、")
      : article.authors;
    return {
      name: article.title_zh,
      artist: authors,
      url: article.audio,
      cover:
        "https://raw.githubusercontent.com/DIYgod/APlayer/master/assets/default.jpg",
    };
  });
}

// 建立文章 HTML
function createArticleHTML(article) {
  // 處理作者顯示，如果超過 3 位則折疊
  let authorsDisplay = "";
  if (Array.isArray(article.authors)) {
    if (article.authors.length > 3) {
      // 顯示前 3 位作者，其餘折疊
      const visibleAuthors = article.authors.slice(0, 3).join("、");
      const allAuthors = article.authors.join("、");
      authorsDisplay = `
        <span class="authors-container">
          <span class="collapsed-view">
            <span class="visible-authors">${visibleAuthors}</span>
            <span class="more-authors-toggle" onclick="toggleAuthors(this)">等 ${
              article.authors.length - 3
            } 位作者</span>
          </span>
          <span class="expanded-view" style="display:none;">
            ${allAuthors}
            <span class="more-authors-toggle" onclick="toggleAuthors(this)">收起</span>
          </span>
        </span>
      `;
    } else {
      authorsDisplay = article.authors.join("、");
    }
  } else {
    authorsDisplay = article.authors;
  }

  // 處理標題和摘要，確保 LaTeX 公式正確顯示
  const title = article.title;
  const title_zh = article.title_zh;
  const summary = article.summary;
  const summary_zh = article.summary_zh;

  const topic = article.query
    ? `<span class="topic">${article.query}</span>`
    : "";
  return `
        <div class="article" data-audio-id="${article.id}">
            ${topic ? `<div class="topic-row">${topic}</div>` : ""}
            <div class="title">
                <a class="title-original tex2jax_process" href="${
                  article.url
                }" target="_blank" style="display:none;">${title}</a>
                <a class="title-translation tex2jax_process" href="${
                  article.url
                }" target="_blank">${title_zh}</a>
            </div>
            <div class="meta">${authorsDisplay} ｜ ${
    article.published_date
  }</div>
            <div class="abstract">
                <span class="abstract-original tex2jax_process" style="display:none;">${summary}</span>
                <span class="abstract-translation tex2jax_process">${summary_zh}</span>
            </div>
        </div>
    `;
}

// 初始化頁面
async function initializePage() {
  const articles = await loadArticles();

  // 初始化音訊播放器
  const ap = new APlayer({
    container: document.getElementById("aplayer"),
    audio: createAudioList(articles),
    theme: "#6366f1",
    lrcType: 0,
    listFolded: false,
    listMaxHeight: 200,
    order: "list",
    controls: ["prev", "play", "next", "progress", "volume", "list"],
  });

  // 顯示文章
  const container = document.getElementById("articles-container");
  container.innerHTML = articles.map(createArticleHTML).join("");

  // 播放速度控制
  const defaultSpeed = 1.25;
  let currentSpeed = defaultSpeed;

  // 設定初始播放速度
  if (ap.audio) {
    ap.audio.playbackRate = defaultSpeed;
  }

  // 當播放器載入新的音訊時，設定播放速度
  ap.on("canplay", () => {
    if (ap.audio) {
      ap.audio.playbackRate = currentSpeed;
    }
  });

  // 添加點擊事件到播放速度按鈕
  document.querySelectorAll(".speed-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const speed = parseFloat(btn.getAttribute("data-speed"));

      // 更新播放速度
      currentSpeed = speed;
      if (ap.audio) {
        ap.audio.playbackRate = speed;
      }

      // 更新按鈕樣式
      document.querySelectorAll(".speed-btn").forEach((b) => {
        b.classList.remove("active");
      });
      btn.classList.add("active");
    });
  });

  // 監聽播放器事件
  function updateCurrentArticle() {
    const currentAudio = ap.list.audios[ap.list.index];
    const currentId = currentAudio.url.split("/").pop().replace(".mp3", "");

    // 移除所有文章的 playing 類別
    document.querySelectorAll(".article").forEach((article) => {
      article.classList.remove("playing");
    });

    // 為當前播放的文章添加 playing 類別
    const currentArticle = document.querySelector(
      `.article[data-audio-id="${currentId}"]`
    );
    if (currentArticle) {
      currentArticle.classList.add("playing");
      // 平滑滾動到當前文章
      setTimeout(() => {
        currentArticle.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 300);
    }
  }

  // 監聽播放和切換曲目事件
  ap.on("play", updateCurrentArticle);
  ap.on("listswitch", updateCurrentArticle);

  // 簡化的 MathJax 渲染，避免過度複雜的 DOM 監聽
  setTimeout(() => {
    try {
      if (window.MathJax) {
        window.MathJax.typeset();
      }
    } catch (e) {
      console.error("MathJax 渲染錯誤:", e);
    }
  }, 1000);
}

// 切換中英文顯示
let showingTranslation = true;
function toggleAll() {
  showingTranslation = !showingTranslation;
  const btn = document.getElementById("toggle-all-btn");
  document
    .querySelectorAll(".title-original")
    .forEach((e) => (e.style.display = showingTranslation ? "none" : ""));
  document
    .querySelectorAll(".title-translation")
    .forEach((e) => (e.style.display = showingTranslation ? "" : "none"));
  document
    .querySelectorAll(".abstract-original")
    .forEach((e) => (e.style.display = showingTranslation ? "none" : ""));
  document
    .querySelectorAll(".abstract-translation")
    .forEach((e) => (e.style.display = showingTranslation ? "" : "none"));
  btn.textContent = showingTranslation ? "顯示原文" : "顯示翻譯";

  // 切換語言後簡單重新渲染 MathJax
  setTimeout(() => {
    try {
      if (window.MathJax) {
        window.MathJax.typeset();
      }
    } catch (e) {
      console.error("MathJax 渲染錯誤:", e);
    }
  }, 500);
}

// 切換作者顯示
function toggleAuthors(element) {
  const authorsContainer = element.closest(".authors-container");
  const collapsedView = authorsContainer.querySelector(".collapsed-view");
  const expandedView = authorsContainer.querySelector(".expanded-view");

  if (collapsedView.style.display !== "none") {
    collapsedView.style.display = "none";
    expandedView.style.display = "inline";
  } else {
    collapsedView.style.display = "inline";
    expandedView.style.display = "none";
  }
}

// 當頁面載入完成時初始化
document.addEventListener("DOMContentLoaded", initializePage);
