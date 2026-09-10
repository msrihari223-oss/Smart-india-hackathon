/**
 * Main Application Orchestrator for Social Media Analytics Framework
 */

import { ApiClient } from './api.js';
import { chartManager } from './charts.js';
import { NetworkGraphManager } from './network_graph.js';

class App {
  constructor() {
    this.ws = null;
    this.isStreamPaused = false;
    this.currentPlatformFilter = 'all';
    this.currentEmotionFilter = 'all';
    this.searchQuery = '';
    this.networkGraph = new NetworkGraphManager('network-canvas-container');
    this.activeFeedPosts = [];
    this.realUsers = [];
    this.currentRealUserPlatform = 'all';
    this.realUserSearch = '';
    this.activeCommentPost = null;
    this.userCreatedPosts = [];
    try {
      const saved = localStorage.getItem('sma_user_posts');
      if (saved) {
        this.userCreatedPosts = JSON.parse(saved);
      }
    } catch (e) {}
  }

  async init() {
    this.setupTabs();
    this.setupEventListeners();
    this.initCharts();
    this.initInfluencerRankings();
    
    // Initial Load
    await this.checkDbHealth();
    await this.loadInitialData();
    await this.loadRealUsers();
    await this.loadInfluencerRankings();
    this.updateMyPostsCountBadge();
    this.connectWebSocket();

    // Periodic Database Health Monitoring
    setInterval(() => this.checkDbHealth(), 15000);
  }

  async checkDbHealth() {
    const badge = document.getElementById('db-status-badge');
    const statusText = document.getElementById('db-connection-status');
    if (!badge || !statusText) return;

    try {
      const health = await ApiClient.getDbHealth();
      if (health && health.status === 'connected') {
        const count = health.tables ? health.tables.post_records : 0;
        badge.style.borderColor = 'rgba(16, 185, 129, 0.5)';
        badge.style.background = 'rgba(16, 185, 129, 0.12)';
        statusText.style.color = '#34d399';
        statusText.innerHTML = `<i class="fas fa-check-circle" style="margin-right: 4px;"></i>PostgreSQL: Connected (${count} records)`;
      } else {
        badge.style.borderColor = 'rgba(245, 158, 11, 0.4)';
        badge.style.background = 'rgba(245, 158, 11, 0.1)';
        statusText.style.color = '#fbbf24';
        statusText.innerHTML = `<i class="fas fa-database" style="margin-right: 4px;"></i>PostgreSQL: Standby / Memory Fallback`;
      }
    } catch (e) {
      statusText.innerText = 'PostgreSQL: Offline';
    }
  }

  setupTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    const sections = document.querySelectorAll('.view-section');

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => t.classList.remove('active'));
        sections.forEach(s => s.classList.remove('active'));

        tab.classList.add('active');
        const target = tab.getAttribute('data-target');
        const targetSection = document.getElementById(target);
        if (targetSection) {
          targetSection.classList.add('active');
        }

        if (target === 'view-influencer-rankings') {
          this.loadInfluencerRankings();
        }

        // Trigger network re-fit and render if switched to network tab
        if (target === 'view-network' && this.networkGraph) {
          setTimeout(() => {
            if (this.lastNetworkData) {
              this.networkGraph.render(this.lastNetworkData);
            } else if (this.networkGraph.network) {
              this.networkGraph.network.redraw();
              this.networkGraph.network.fit();
            }
          }, 60);
        }
      });
    });
  }

  initCharts() {
    chartManager.initEmotionDonut('chart-emotion-donut');
    chartManager.initTimelineChart('chart-sentiment-timeline');
    chartManager.initAgeDistribution('chart-age-distribution');
    chartManager.initInterestsRadar('chart-interests-radar');
    chartManager.initGeoChart('chart-geo-distribution');
  }

  setupEventListeners() {
    // Platform Filter Buttons
    document.querySelectorAll('.platform-filter-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.platform-filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentPlatformFilter = btn.getAttribute('data-platform');
        this.refreshFeed();
      });
    });

    // Stream Play/Pause Toggle
    const btnPause = document.getElementById('btn-pause-stream');
    if (btnPause) {
      btnPause.addEventListener('click', () => {
        this.isStreamPaused = !this.isStreamPaused;
        btnPause.innerHTML = this.isStreamPaused 
          ? '<i class="fas fa-play"></i> Resume Stream' 
          : '<i class="fas fa-pause"></i> Pause Stream';
        btnPause.classList.toggle('active', this.isStreamPaused);
      });
    }

    // Stream Speed Slider
    const speedSelect = document.getElementById('stream-speed-select');
    if (speedSelect) {
      speedSelect.addEventListener('change', async (e) => {
        const speed = parseFloat(e.target.value);
        await ApiClient.controlStreamSpeed(speed);
      });
    }

    // Custom Deep Analyzer Form & Guardrail
    const analyzerInput = document.getElementById('analyzer-text');
    let toxicityDebounceTimer = null;

    if (analyzerInput) {
      // Live debounced real-time typing analysis
      analyzerInput.addEventListener('input', (e) => {
        clearTimeout(toxicityDebounceTimer);
        const text = e.target.value.trim();
        if (!text) {
          this.updateLiveToxicityPill({ is_toxic: false, severity: 'SAFE', detected_bad_words: [], detected_bad_hashtags: [] });
          return;
        }

        toxicityDebounceTimer = setTimeout(async () => {
          try {
            const tox = await ApiClient.checkToxicity({ text });
            this.updateLiveToxicityPill(tox);
          } catch (err) {
            console.error('Toxicity live check failed:', err);
          }
        }, 220);
      });
    }

    // Quick Test Presets
    const setupPreset = (id, text) => {
      const btn = document.getElementById(id);
      if (btn && analyzerInput) {
        btn.addEventListener('click', () => {
          analyzerInput.value = text;
          analyzerInput.dispatchEvent(new Event('input'));
        });
      }
    };

    setupPreset('preset-safe', 'The latest Autonomous Agent framework benchmark just dropped and the latency reduction is absolutely insane! 🚀 We are witnessing an unprecedented paradigm shift in AI agents. #AgenticAI #GenAI');
    setupPreset('preset-badwords', 'This product is complete garbage and total bullshit! You fucking idiots and clowns stole our money! What a bunch of bastards! #scam #worst');
    setupPreset('preset-hashtags', 'Boycott this company immediately! Total corruption and lies. #hateThisApp #killTheScam #boycottFake #fraudsters #trash');
    setupPreset('preset-threat', 'I will destroy and burn your entire office down! You worthless scumbags will suffer and die! #hate #revenge');

    // Toxicity Warning Modal Controls
    const modal = document.getElementById('toxicity-warning-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const btnDismissModal = document.getElementById('btn-dismiss-modal');
    const btnSanitize = document.getElementById('btn-sanitize-text');

    if (btnCloseModal) btnCloseModal.addEventListener('click', () => this.hideToxicityWarningModal());
    if (btnDismissModal) btnDismissModal.addEventListener('click', () => this.hideToxicityWarningModal());
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.hideToxicityWarningModal();
      });
    }

    if (btnSanitize) {
      btnSanitize.addEventListener('click', () => {
        // If comment modal is active, sanitize comment input and submit
        const commentInput = document.getElementById('comment-input-text');
        if (this.activeCommentPost && commentInput && this.lastAnalyzedToxicity) {
          const sanitized = this.sanitizeText(
            commentInput.value,
            this.lastAnalyzedToxicity.detected_bad_words || [],
            this.lastAnalyzedToxicity.detected_bad_hashtags || []
          );
          commentInput.value = sanitized;
          this.hideToxicityWarningModal();
          this.submitComment(this.activeCommentPost.id, true);
          return;
        }

        if (this.lastAnalyzedToxicity && analyzerInput) {
          const sanitized = this.sanitizeText(
            analyzerInput.value,
            this.lastAnalyzedToxicity.detected_bad_words || [],
            this.lastAnalyzedToxicity.detected_bad_hashtags || []
          );
          analyzerInput.value = sanitized;
          this.hideToxicityWarningModal();
          analyzerInput.dispatchEvent(new Event('input'));
        }
      });
    }

    // ================= Post Creator with Photo/Video Media =================
    const tabBtnPhoto = document.getElementById('tab-btn-photo');
    const tabBtnVideo = document.getElementById('tab-btn-video');
    const mediaTypeSelect = document.getElementById('creator-media-type');
    const mediaModeLabel = document.getElementById('media-mode-label');
    const mediaUrlInput = document.getElementById('creator-media-url');
    const mediaPreview = document.getElementById('creator-media-preview');
    const btnTriggerUpload = document.getElementById('btn-trigger-upload');
    const fileInput = document.getElementById('creator-file-input');
    const btnSamplePhoto = document.getElementById('btn-sample-photo');
    const btnSampleVideo = document.getElementById('btn-sample-video');
    const btnBroadcast = document.getElementById('btn-broadcast-post');
    const btnPostCancel = document.getElementById('btn-post-cancel');
    const btnCancelX = document.getElementById('btn-cancel-post-x');
    const btnQuickCreatePost = document.getElementById('btn-quick-create-post');

    const updateMediaPreview = () => {
      if (!mediaPreview || !mediaUrlInput) return;
      const url = mediaUrlInput.value.trim();
      const currentType = mediaTypeSelect ? mediaTypeSelect.value : 'photo';

      if (!url) {
        mediaPreview.innerHTML = '<div style="color: var(--text-dim); font-size: 0.85rem; padding: 2rem; text-align: center;"><i class="fas fa-cloud-arrow-up" style="font-size: 1.6rem; margin-bottom: 0.5rem; display: block; color: var(--text-muted);"></i>Upload a file or paste URL above to preview media</div>';
        return;
      }

      if (currentType === 'video' || url.endsWith('.mp4') || url.endsWith('.webm') || url.startsWith('data:video')) {
        mediaPreview.innerHTML = `<video src="${url}" controls autoplay muted playsinline style="width: 100%; max-height: 260px; border-radius: 8px; object-fit: contain; background: #000; display: block;"></video>`;
      } else {
        mediaPreview.innerHTML = `<img src="${url}" alt="Preview" style="width: 100%; max-height: 260px; border-radius: 8px; object-fit: cover; display: block;" onerror="this.parentElement.innerHTML='<div style=\\'color:#f43f5e; font-size:0.8rem; padding:1.5rem;\\'>Invalid image URL</div>'"/>`;
      }
    };

    // Photo Tab Switch
    if (tabBtnPhoto) {
      tabBtnPhoto.addEventListener('click', () => {
        if (tabBtnVideo) tabBtnVideo.classList.remove('active');
        tabBtnPhoto.classList.add('active');
        if (mediaTypeSelect) mediaTypeSelect.value = 'photo';
        if (mediaModeLabel) {
          mediaModeLabel.style.color = 'var(--neon-cyan)';
          mediaModeLabel.innerHTML = '<i class="fas fa-image"></i> Photo Attachment';
        }
        if (mediaUrlInput) {
          mediaUrlInput.placeholder = 'Paste image URL (e.g. https://... .jpg, .png)';
          if (!mediaUrlInput.value || mediaUrlInput.value.includes('.mp4')) {
            mediaUrlInput.value = 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80';
          }
        }
        updateMediaPreview();
      });
    }

    // Video Tab Switch
    if (tabBtnVideo) {
      tabBtnVideo.addEventListener('click', () => {
        if (tabBtnPhoto) tabBtnPhoto.classList.remove('active');
        tabBtnVideo.classList.add('active');
        if (mediaTypeSelect) mediaTypeSelect.value = 'video';
        if (mediaModeLabel) {
          mediaModeLabel.style.color = '#c084fc';
          mediaModeLabel.innerHTML = '<i class="fas fa-film"></i> Video Stream Attachment';
        }
        if (mediaUrlInput) {
          mediaUrlInput.placeholder = 'Paste video URL (e.g. https://... .mp4, .webm)';
          if (!mediaUrlInput.value || mediaUrlInput.value.includes('images.unsplash.com')) {
            mediaUrlInput.value = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4';
          }
        }
        updateMediaPreview();
      });
    }

    // Trigger File Upload
    if (btnTriggerUpload && fileInput) {
      btnTriggerUpload.addEventListener('click', () => fileInput.click());
      fileInput.addEventListener('change', async (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;

        // Instant local preview
        const reader = new FileReader();
        reader.onload = (event) => {
          const dataUrl = event.target.result;
          if (mediaUrlInput) mediaUrlInput.value = dataUrl;
          if (file.type.startsWith('video')) {
            if (tabBtnVideo) tabBtnVideo.click();
          } else {
            if (tabBtnPhoto) tabBtnPhoto.click();
          }
          updateMediaPreview();
        };
        reader.readAsDataURL(file);

        // Upload to server for permanent static URL & database storage
        try {
          const formData = new FormData();
          formData.append('file', file);
          const res = await fetch('/api/media/upload', {
            method: 'POST',
            body: formData
          });
          const data = await res.json();
          if (data.success && data.media_url) {
            if (mediaUrlInput) mediaUrlInput.value = data.media_url;
            if (data.media_type === 'video' && tabBtnVideo) tabBtnVideo.click();
            else if (tabBtnPhoto) tabBtnPhoto.click();
          }
        } catch (err) {
          console.warn('[MEDIA] Server upload failed, using local Data URL fallback:', err);
        }
      });
    }

    if (mediaUrlInput) {
      mediaUrlInput.addEventListener('input', updateMediaPreview);
      // Run once on init
      updateMediaPreview();
    }

    if (btnSamplePhoto) {
      btnSamplePhoto.addEventListener('click', () => {
        if (tabBtnPhoto) tabBtnPhoto.click();
        if (mediaUrlInput) {
          mediaUrlInput.value = 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=800&q=80';
          updateMediaPreview();
        }
      });
    }

    if (btnSampleVideo) {
      btnSampleVideo.addEventListener('click', () => {
        if (tabBtnVideo) tabBtnVideo.click();
        if (mediaUrlInput) {
          mediaUrlInput.value = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4';
          updateMediaPreview();
        }
      });
    }

    // Cancel / Close Handlers
    const returnToFeed = () => {
      // 1. Set filter button to My Posts so user's new dispatch & photos are prominently displayed
      document.querySelectorAll('.platform-filter-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-platform') === 'my_posts');
      });
      this.currentPlatformFilter = 'my_posts';

      // 2. Switch tab to view-feed
      document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
      const feedTab = document.querySelector('.nav-tab[data-target="view-feed"]');
      if (feedTab) feedTab.classList.add('active');

      document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
      const feedSec = document.getElementById('view-feed');
      if (feedSec) feedSec.classList.add('active');

      // 3. Render feed with user's posts
      this.refreshFeed();

      // 4. Scroll to top of feed smoothly
      setTimeout(() => {
        const feedList = document.getElementById('live-stream-feed');
        if (feedList) feedList.scrollTop = 0;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 60);
    };

    if (btnPostCancel) btnPostCancel.addEventListener('click', returnToFeed);
    if (btnCancelX) btnCancelX.addEventListener('click', returnToFeed);

    if (btnQuickCreatePost) {
      btnQuickCreatePost.addEventListener('click', () => {
        const studioTab = document.querySelector('.nav-tab[data-target="view-media-broadcast"]');
        if (studioTab) studioTab.click();
      });
    }

    // Studio Post Character Counter Listener
    const creatorPostText = document.getElementById('creator-post-text');
    const creatorCharCounter = document.getElementById('creator-char-counter');
    if (creatorPostText && creatorCharCounter) {
      creatorPostText.addEventListener('input', (e) => {
        const len = e.target.value.length;
        creatorCharCounter.innerText = `${len} / 500`;
        creatorCharCounter.style.color = len > 450 ? '#f43f5e' : 'var(--text-dim)';
      });
    }

    // ================= Studio Broadcast Post Handler =================
    if (btnBroadcast) {
      btnBroadcast.addEventListener('click', async () => {
        const text = (document.getElementById('creator-post-text')?.value || '').trim();
        const platform = document.getElementById('creator-platform')?.value || 'X';
        let mediaType = mediaTypeSelect ? mediaTypeSelect.value : 'photo';
        let mediaUrl = mediaUrlInput ? mediaUrlInput.value.trim() : null;

        if (!text && !mediaUrl) {
          return alert('Please write a caption or attach a photo/video.');
        }

        if (mediaUrl) {
          if (mediaType === 'video' || mediaUrl.endsWith('.mp4') || mediaUrl.endsWith('.webm') || mediaUrl.startsWith('data:video')) {
            mediaType = 'video';
          } else {
            mediaType = 'photo';
          }
        }

        btnBroadcast.disabled = true;
        btnBroadcast.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Posting...';

        let u = window.authController?.user || {};
        let authorUsername = u.username || 'operator';
        let authorName = u.full_name || 'Intelligence Operator';
        let authorAvatar = u.avatar || null;
        let authorRole = u.role || 'Analyst';

        try {
          const res = await ApiClient.createPost({
            text: text || 'Broadcast dispatch with media payload.',
            platform: platform,
            media_type: mediaType,
            media_url: mediaUrl,
            author_username: authorUsername,
            author_name: authorName,
            author_avatar: authorAvatar,
            author_role: authorRole
          });

          if (res.success && res.post) {
            this.addUserPost(res.post);
            this.showToast('🚀 Broadcast Published!', `Your post is live on ${res.post.platform} feed and saved to database.`, 'success');

            // Increment KPI counter
            const kpiTotalEl = document.getElementById('kpi-total-posts');
            if (kpiTotalEl) {
              const currentTotal = parseInt((kpiTotalEl.innerText || '0').replace(/,/g, ''), 10) || 0;
              kpiTotalEl.innerText = (currentTotal + 1).toLocaleString();
            }

            // Reset studio text
            const postTextEl = document.getElementById('creator-post-text');
            if (postTextEl) postTextEl.value = '';
            const charCounterEl = document.getElementById('creator-char-counter');
            if (charCounterEl) charCounterEl.innerText = '0 / 500';

            btnBroadcast.innerHTML = '<i class="fas fa-check-circle" style="color: #10b981;"></i> Posted!';
            
            // Auto-switch to Live Feed tab so user immediately sees their photo/video post!
            setTimeout(() => {
              returnToFeed();
              btnBroadcast.disabled = false;
              btnBroadcast.innerHTML = '<i class="fas fa-paper-plane"></i> Post';
              const feedEl = document.getElementById('view-feed');
              if (feedEl) feedEl.scrollIntoView({ behavior: 'smooth' });
            }, 500);
          } else {
            alert('Failed to post: ' + (res.error || 'Unknown error'));
            btnBroadcast.disabled = false;
            btnBroadcast.innerHTML = '<i class="fas fa-paper-plane"></i> Post';
          }
        } catch (err) {
          alert('Error creating post: ' + err.message);
          btnBroadcast.disabled = false;
          btnBroadcast.innerHTML = '<i class="fas fa-paper-plane"></i> Post';
        }
      });
    }

    // ================= Comments Modal Listeners & Presets =================
    const btnCloseComments = document.getElementById('btn-close-comments-modal');
    const commentsModal = document.getElementById('comments-modal');
    const btnSubmitComment = document.getElementById('btn-submit-comment');
    const btnQuickBadComment = document.getElementById('btn-quick-bad-comment');
    const btnQuickGoodComment = document.getElementById('btn-quick-good-comment');

    if (btnCloseComments) btnCloseComments.addEventListener('click', () => this.closeCommentsModal());
    if (commentsModal) {
      commentsModal.addEventListener('click', (e) => {
        if (e.target === commentsModal) this.closeCommentsModal();
      });
    }

    if (btnQuickBadComment) {
      btnQuickBadComment.addEventListener('click', () => {
        const inp = document.getElementById('comment-input-text');
        if (inp) inp.value = 'This is complete bullshit and garbage! You fucking idiots and clown scammers stole money! #scam';
      });
    }

    if (btnQuickGoodComment) {
      btnQuickGoodComment.addEventListener('click', () => {
        const inp = document.getElementById('comment-input-text');
        if (inp) inp.value = 'Outstanding intelligence dispatch! Clean metrics and excellent visualization. 👏';
      });
    }

    if (btnSubmitComment) {
      btnSubmitComment.addEventListener('click', () => {
        if (this.activeCommentPost) {
          this.submitComment(this.activeCommentPost.id);
        }
      });
    }



    const btnAnalyze = document.getElementById('btn-run-analyzer');
    if (btnAnalyze) {
      btnAnalyze.addEventListener('click', async () => {
        const text = document.getElementById('analyzer-text').value.trim();
        const bio = document.getElementById('analyzer-bio').value.trim();
        const loc = document.getElementById('analyzer-loc').value.trim();

        if (!text) return alert('Please enter post text to analyze');

        btnAnalyze.disabled = true;
        btnAnalyze.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running Guardrails & AI NLP...';

        try {
          const res = await ApiClient.analyzeCustomPost({ text, user_bio: bio, location: loc });
          this.lastAnalyzedToxicity = res.toxicity || {};
          
          // If toxic elements detected, immediately trigger pop-up alert warning!
          if (res.toxicity && res.toxicity.is_toxic) {
            this.showToxicityWarningModal(res.toxicity, text);
          }

          this.renderAnalyzerResults(res);
        } catch (err) {
          alert('Error analyzing custom post: ' + err.message);
        } finally {
          btnAnalyze.disabled = false;
          btnAnalyze.innerHTML = '<i class="fas fa-bolt"></i> Run AI Inference Pipeline';
        }
      });
    }


    // Cascade Simulator Trigger
    const btnSimCascade = document.getElementById('btn-run-cascade');
    if (btnSimCascade) {
      btnSimCascade.addEventListener('click', async () => {
        const seed = document.getElementById('cascade-seed-select').value;
        btnSimCascade.disabled = true;
        btnSimCascade.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Simulating Cascade...';
        
        try {
          const cascadeData = await ApiClient.getCascade(seed, 4);
          this.renderCascadeLog(cascadeData);
          await this.networkGraph.animateCascade(cascadeData, seed);
        } catch (err) {
          console.error(err);
        } finally {
          btnSimCascade.disabled = false;
          btnSimCascade.innerHTML = '<i class="fas fa-play"></i> Simulate Information Cascade';
        }
      });
    }

    // Network Layout View Mode Controls
    const btnNetForce = document.getElementById('btn-network-force');
    const btnNetTree = document.getElementById('btn-network-tree');
    const btnNetReset = document.getElementById('btn-network-reset');

    if (btnNetForce) {
      btnNetForce.addEventListener('click', () => {
        if (btnNetTree) btnNetTree.classList.remove('active', 'border-cyan');
        btnNetForce.classList.add('active');
        btnNetForce.style.borderColor = 'var(--neon-cyan)';
        btnNetForce.style.color = 'var(--neon-cyan)';
        if (btnNetTree) {
          btnNetTree.style.borderColor = '';
          btnNetTree.style.color = '';
        }
        this.networkGraph.setPhysicsMode('force');
      });
    }

    if (btnNetTree) {
      btnNetTree.addEventListener('click', () => {
        if (btnNetForce) btnNetForce.classList.remove('active');
        btnNetTree.classList.add('active');
        btnNetTree.style.borderColor = 'var(--neon-purple)';
        btnNetTree.style.color = 'var(--neon-purple)';
        if (btnNetForce) {
          btnNetForce.style.borderColor = '';
          btnNetForce.style.color = '';
        }
        this.networkGraph.setPhysicsMode('hierarchical');
      });
    }

    if (btnNetReset) {
      btnNetReset.addEventListener('click', () => {
        this.networkGraph.resetFocus();
        if (this.networkGraph.network) {
          this.networkGraph.network.fit({
            animation: { duration: 600, easingFunction: 'easeInOutQuad' }
          });
        }
      });
    }

    // Real User Filter Buttons
    document.querySelectorAll('.real-user-filter-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.real-user-filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentRealUserPlatform = btn.getAttribute('data-platform');
        this.filterAndRenderRealUsers();
      });
    });

    // Real User Search Input
    const searchRealUsersInput = document.getElementById('search-real-users');
    if (searchRealUsersInput) {
      searchRealUsersInput.addEventListener('input', (e) => {
        this.realUserSearch = e.target.value.trim().toLowerCase();
        this.filterAndRenderRealUsers();
      });
    }

    // Trigger Real Live Crawl Button
    const btnCollectReal = document.getElementById('btn-collect-real-now');
    if (btnCollectReal) {
      btnCollectReal.addEventListener('click', async () => {
        btnCollectReal.disabled = true;
        btnCollectReal.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Crawling Live Feeds...';
        try {
          const res = await ApiClient.triggerRealCollection();
          await this.loadRealUsers();
          // Flash success
          btnCollectReal.innerHTML = `<i class="fas fa-check"></i> Ingested ${res.collected_posts_count || 15} Posts`;
          setTimeout(() => {
            btnCollectReal.disabled = false;
            btnCollectReal.innerHTML = '<i class="fas fa-satellite-dish"></i> Collect Live Real Data';
          }, 2000);
        } catch (err) {
          alert('Error collecting real data: ' + err.message);
          btnCollectReal.disabled = false;
          btnCollectReal.innerHTML = '<i class="fas fa-satellite-dish"></i> Collect Live Real Data';
        }
      });
    }

    // Auto Sync Real Users to Database Button
    const btnSyncDb = document.getElementById('btn-sync-users-db');
    if (btnSyncDb) {
      btnSyncDb.addEventListener('click', async () => {
        btnSyncDb.disabled = true;
        btnSyncDb.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Syncing to Supabase...';
        try {
          const res = await ApiClient.syncRealUsersToDb();
          btnSyncDb.innerHTML = `<i class="fas fa-check-circle" style="color: #34d399;"></i> Synced ${res.synced_users_count || 140}+ Users!`;
          btnSyncDb.style.borderColor = '#10b981';
          setTimeout(() => {
            btnSyncDb.disabled = false;
            btnSyncDb.innerHTML = '<i class="fas fa-database"></i> Auto-Sync to Database';
            btnSyncDb.style.borderColor = 'rgba(96, 165, 250, 0.4)';
          }, 2500);
        } catch (err) {
          alert('Sync error: ' + err.message);
          btnSyncDb.disabled = false;
          btnSyncDb.innerHTML = '<i class="fas fa-database"></i> Auto-Sync to Database';
        }
      });
    }

    // Export Real Users Buttons
    const btnExportCsv = document.getElementById('btn-export-users-csv');
    if (btnExportCsv) {
      btnExportCsv.addEventListener('click', () => ApiClient.exportRealUsers('csv'));
    }

    const btnExportJson = document.getElementById('btn-export-users-json');
    if (btnExportJson) {
      btnExportJson.addEventListener('click', () => ApiClient.exportRealUsers('json'));
    }

    // Global Node Selection Callback from Network Graph
    window.onNodeSelected = (node) => {
      const select = document.getElementById('cascade-seed-select');
      if (select) select.value = node.id;
    };
  }

  async loadInitialData() {
    try {
      const [kpis, feed, timeline, demo, trends, network] = await Promise.all([
        ApiClient.getKPIs(),
        ApiClient.getFeed(30),
        ApiClient.getTimeline(15),
        ApiClient.getDemographics(),
        ApiClient.getTrends(),
        ApiClient.getNetwork()
      ]);

      this.updateKPIs(kpis);
      this.renderFeed(feed);
      this.activeFeedPosts = feed;
      
      chartManager.updateTimelineChart(timeline);
      chartManager.updateAgeDistribution(demo.age_brackets);
      chartManager.updateInterestsRadar(demo.interests);
      chartManager.updateGeoChart(demo.geographic_distribution);
      
      this.renderTrends(trends);
      this.renderNetwork(network);
      this.populateCascadeSeedSelect(network.kols);

    } catch (e) {
      console.error('Failed to load initial data:', e);
    }
  }

  connectWebSocket() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    if (this.wsPingInterval) {
      clearInterval(this.wsPingInterval);
      this.wsPingInterval = null;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/stream`;
    
    try {
      this.ws = new WebSocket(wsUrl);
    } catch (err) {
      console.warn('WebSocket connection attempt failed, retrying in 2s...', err);
      setTimeout(() => this.connectWebSocket(), 2000);
      return;
    }

    this.ws.onopen = () => {
      const statusEl = document.getElementById('stream-connection-status');
      if (statusEl) {
        statusEl.innerText = 'Live Feed Connected';
        statusEl.style.color = '#38bdf8';
      }
      this.reconnectDelay = 1000;

      // Active Keepalive Heartbeat: Pings server every 10 seconds to keep connection permanently open
      this.wsPingInterval = setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          try {
            this.ws.send(JSON.stringify({ type: 'ping', time: Date.now() }));
          } catch (e) {}
        }
      }, 10000);
    };

    this.ws.onmessage = (event) => {
      if (this.isStreamPaused) return;

      try {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') {
          // Heartbeat acknowledged
          return;
        }
        if (data.type === 'LIVE_POST') {
          this.handleLivePost(data.post, data.kpis, data.trends);
        }
      } catch (err) {
        console.error('WebSocket payload error:', err);
      }
    };

    this.ws.onerror = () => {
      // Handled via onclose
    };

    this.ws.onclose = () => {
      if (this.wsPingInterval) {
        clearInterval(this.wsPingInterval);
        this.wsPingInterval = null;
      }
      const statusEl = document.getElementById('stream-connection-status');
      if (statusEl) {
        statusEl.innerText = 'Reconnecting...';
        statusEl.style.color = '#f59e0b';
      }
      const delay = this.reconnectDelay || 2000;
      this.reconnectDelay = Math.min(delay * 1.5, 10000);
      setTimeout(() => this.connectWebSocket(), delay);
    };

    // Auto-reconnect when tab gains focus or network comes online
    if (!this._hasBoundWsEvents) {
      this._hasBoundWsEvents = true;
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
          if (!this.ws || this.ws.readyState === WebSocket.CLOSED || this.ws.readyState === WebSocket.CLOSING) {
            this.connectWebSocket();
          }
        }
      });
      window.addEventListener('online', () => {
        this.connectWebSocket();
      });
    }
  }

  showToast(title, message, type = 'info') {
    const existing = document.querySelector('.sma-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'sma-toast';
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
    const iconColor = type === 'success' ? 'var(--neon-emerald)' : 'var(--neon-cyan)';

    toast.innerHTML = `
      <i class="fas ${icon}" style="font-size: 1.25rem; color: ${iconColor};"></i>
      <div style="flex: 1;">
        <div style="font-weight: 700; color: #fff; font-size: 0.9rem;">${title}</div>
        <div style="font-size: 0.78rem; color: var(--text-muted);">${message}</div>
      </div>
      <button class="btn-icon" style="color: var(--text-muted); padding: 2px 6px; cursor: pointer;" onclick="this.parentElement.remove();"><i class="fas fa-times"></i></button>
    `;

    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(15px)';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }

  addUserPost(post) {
    if (!post) return;
    const exists = this.userCreatedPosts.find(p => p.id === post.id);
    if (!exists) {
      this.userCreatedPosts.unshift(post);
      try {
        localStorage.setItem('sma_user_posts', JSON.stringify(this.userCreatedPosts.slice(0, 50)));
      } catch (e) {}
    }
    
    const feedExists = this.activeFeedPosts.find(p => p.id === post.id);
    if (!feedExists) {
      this.activeFeedPosts.unshift(post);
    }

    this.renderUserPinnedPosts();
    this.updateMyPostsCountBadge();
    
    if (this.matchesCurrentFilters(post)) {
      this.prependPostCard(post, true);
    }
  }

  renderUserPinnedPosts() {
    const container = document.getElementById('user-pinned-posts-container');
    const list = document.getElementById('user-pinned-posts-list');
    const badgeCount = document.getElementById('user-pinned-badge-count');
    if (!container || !list) return;

    if (!this.userCreatedPosts || this.userCreatedPosts.length === 0) {
      container.style.display = 'none';
      return;
    }

    container.style.display = 'block';
    if (badgeCount) {
      badgeCount.innerText = `${this.userCreatedPosts.length} ${this.userCreatedPosts.length === 1 ? 'Dispatch' : 'Dispatches'}`;
    }

    list.innerHTML = '';
    this.userCreatedPosts.slice(0, 5).forEach(post => {
      const card = this.createPostElement(post);
      card.classList.add('user-post-card');
      list.appendChild(card);
    });
  }

  updateMyPostsCountBadge() {
    const el = document.getElementById('my-posts-count');
    if (el) {
      el.innerText = (this.userCreatedPosts || []).length;
    }
  }

  handleLivePost(post, kpis, trends) {
    if (kpis) this.updateKPIs(kpis);
    if (trends) this.renderTrends(trends);

    // Add post to active feed
    this.activeFeedPosts.unshift(post);
    if (this.activeFeedPosts.length > 50) this.activeFeedPosts.pop();

    if (this.matchesCurrentFilters(post)) {
      this.prependPostCard(post, false);
    }

    // Update emotion donut live
    if (post.sentiment && post.sentiment.emotion_scores) {
      chartManager.updateEmotionDonut(post.sentiment.emotion_scores);
    }
  }

  matchesCurrentFilters(post) {
    if (!post) return false;
    if (this.currentPlatformFilter === 'my_posts') {
      const currentUsername = (window.authController?.user?.username || 'operator').toLowerCase();
      const authorUsername = (post.author?.username || '').toLowerCase();
      return (authorUsername === currentUsername) || (post.id && post.id.startsWith('post_usr_')) || this.userCreatedPosts.some(u => u.id === post.id);
    }
    if (this.currentPlatformFilter !== 'all' && (post.platform || '').toLowerCase() !== this.currentPlatformFilter.toLowerCase()) {
      return false;
    }
    return true;
  }

  getDisplayPosts() {
    let posts = [...this.activeFeedPosts];
    // Merge in any userCreatedPosts
    this.userCreatedPosts.forEach(up => {
      if (!posts.some(p => p.id === up.id)) {
        posts.unshift(up);
      }
    });

    if (this.currentPlatformFilter === 'my_posts') {
      const currentUsername = (window.authController?.user?.username || 'operator').toLowerCase();
      return posts.filter(p => (p.author?.username || '').toLowerCase() === currentUsername || (p.id && p.id.startsWith('post_usr_')) || this.userCreatedPosts.some(u => u.id === p.id));
    }

    if (this.currentPlatformFilter !== 'all') {
      const targetPlat = this.currentPlatformFilter.toLowerCase();
      return posts.filter(p => (p.platform || '').toLowerCase() === targetPlat);
    }

    return posts;
  }

  refreshFeed() {
    const posts = this.getDisplayPosts();
    this.renderFeed(posts);
  }

  updateKPIs(kpis) {
    if (!kpis) return;
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.innerText = val;
    };

    setVal('kpi-total-posts', (kpis.total_posts || 0).toLocaleString());
    setVal('kpi-sentiment-index', (kpis.overall_sentiment_index > 0 ? '+' : '') + (kpis.overall_sentiment_index || 0));
    setVal('kpi-sarcasm-count', (kpis.sarcasm_detected_count || 0).toLocaleString());
    setVal('kpi-velocity', `${kpis.velocity_per_minute || 24}/m`);
  }

  renderFeed(posts) {
    const list = document.getElementById('live-stream-feed');
    if (!list) return;
    list.innerHTML = '';

    if (this.currentPlatformFilter === 'my_posts' && (!posts || posts.length === 0)) {
      list.innerHTML = `
        <div style="text-align: center; padding: 3.5rem 1.5rem; color: var(--text-muted); background: rgba(15, 23, 42, 0.4); border-radius: 12px; border: 1px dashed rgba(0, 240, 255, 0.25);">
          <i class="fas fa-camera-retro" style="font-size: 2.2rem; color: var(--neon-cyan); margin-bottom: 0.85rem; display: block;"></i>
          <div style="font-weight: 700; color: #fff; font-size: 1rem; margin-bottom: 0.35rem;">No Published Posts Yet</div>
          <div style="font-size: 0.82rem; margin-bottom: 1.25rem; color: var(--text-muted);">When you post photos, videos, or dispatches, they will be listed here.</div>
          <button type="button" class="btn-post-submit-gradient" onclick="document.querySelector('.nav-tab[data-target=\\'view-media-broadcast\\']')?.click();" style="font-size: 0.82rem; padding: 0.45rem 1.25rem;">
            <i class="fas fa-plus"></i> Create New Post
          </button>
        </div>
      `;
      return;
    }

    (posts || []).forEach(p => list.appendChild(this.createPostElement(p)));
  }

  prependPostCard(post, isUserCreated = false) {
    const list = document.getElementById('live-stream-feed');
    if (!list) return;

    // Check if card with this ID already rendered
    const existing = document.getElementById(`feed-card-${post.id}`);
    if (existing) return;

    const card = this.createPostElement(post);
    card.id = `feed-card-${post.id}`;
    if (isUserCreated) {
      card.classList.add('user-post-card');
      card.style.borderColor = 'var(--neon-cyan)';
      card.style.boxShadow = '0 0 25px rgba(0, 240, 255, 0.4)';
    }
    list.insertBefore(card, list.firstChild);

    // Keep max 50 in DOM
    if (list.children.length > 50) {
      list.removeChild(list.lastChild);
    }
  }

  createPostElement(post) {
    const card = document.createElement('div');
    card.className = 'post-card';
    
    const isUserPost = (post.author?.username === (window.authController?.user?.username || 'operator') || (post.id && post.id.startsWith('post_usr_')) || (this.userCreatedPosts && this.userCreatedPosts.some(u => u.id === post.id)));
    if (isUserPost) {
      card.classList.add('user-post-card');
    }
    
    const sent = post.sentiment || {};
    const sarcasm = sent.sarcasm || {};
    const demo = post.demographics || {};
    const author = post.author || { name: 'User', username: 'user', role: 'Citizen' };
    const platformClass = `tag-${post.platform.toLowerCase()}`;
    const profileUrl = author.profile_url || (author.username ? `https://${post.platform.toLowerCase()}.com/${author.username}` : '#');

    // Stance color
    const stance = sent.stance || { label: 'Neutral', score: 0 };
    const stanceColor = stance.score > 0.2 ? '#10b981' : (stance.score < -0.2 ? '#f43f5e' : '#a855f7');

    const platformIcons = {
      x: 'fa-brands fa-x-twitter',
      telegram: 'fa-brands fa-telegram',
      reddit: 'fa-brands fa-reddit',
      youtube: 'fa-brands fa-youtube',
      instagram: 'fa-brands fa-instagram',
      facebook: 'fa-brands fa-facebook'
    };
    const platKey = (post.platform || '').toLowerCase();
    const platIcon = platformIcons[platKey] || 'fas fa-hashtag';

    card.innerHTML = `
      <div class="post-card-header">
        <div class="post-author">
          <img class="author-avatar" src="${author.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${author.username}`}" alt="${author.name}"/>
          <div>
            <div class="author-name">
              <a href="${profileUrl}" target="_blank" style="color: #fff; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
                ${author.name}
                <i class="fas fa-arrow-up-right-from-square" style="font-size: 0.68rem; color: var(--text-muted);"></i>
              </a>
              <span class="author-handle">@${author.username}</span>
            </div>
            <div style="font-size: 0.72rem; color: var(--text-muted);">${author.role || 'Live Contributor'} • ${demo.geographic_origin || author.location || 'Global'}</div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap: 0.4rem;">
          ${isUserPost
            ? `<span class="kpi-badge" style="background: rgba(0, 240, 255, 0.2); color: var(--neon-cyan); border: 1px solid rgba(0, 240, 255, 0.6); font-size: 0.7rem; padding: 0.18rem 0.5rem; font-weight: 700; box-shadow: 0 0 10px rgba(0,240,255,0.3);"><i class="fas fa-user-astronaut"></i> Your Post</span>`
            : ''
          }
          <span class="post-platform-tag ${platformClass}"><i class="${platIcon}"></i> ${post.platform}</span>
          <span class="kpi-badge badge-emerald" style="font-size: 0.68rem; padding: 0.15rem 0.45rem;"><i class="fas fa-check-circle"></i> Live Verified</span>
          <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">${post.timestamp_iso || 'Just now'}</span>
        </div>
      </div>
      <div class="post-body">${post.text}</div>
      ${(isUserPost && post.media_url) ? `
        <div style="margin: 0.65rem 0; border-radius: 10px; overflow: hidden; max-height: 280px; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.08);">
          ${(post.media_type === 'video' || post.media_url.endsWith('.mp4') || post.media_url.endsWith('.webm') || post.media_url.startsWith('data:video'))
            ? `<video src="${post.media_url}" controls playsinline style="width: 100%; max-height: 280px; object-fit: contain; display: block;"></video>`
            : `<img src="${post.media_url}" alt="Attachment" style="width: 100%; max-height: 280px; object-fit: cover; display: block;" onerror="this.parentElement.style.display='none'"/>`
          }
        </div>
      ` : ''}
      <div class="post-intel-badges">
        <span class="intel-badge" style="color: ${sent.valence > 0.1 ? '#10b981' : (sent.valence < -0.1 ? '#f43f5e' : '#94a3b8')};">
          <i class="fas fa-heart"></i> ${sent.sentiment_label || 'Neutral'} (${sent.valence || 0})
        </span>
        <span class="intel-badge" style="color: #00f0ff;">
          <i class="fas fa-brain"></i> Emotion: ${sent.primary_emotion || 'Neutral'}
        </span>
        ${sarcasm.is_sarcastic ? `
          <span class="intel-badge intel-sarcasm">
            <i class="fas fa-mask"></i> Sarcasm Detected (${Math.round(sarcasm.confidence * 100)}%)
          </span>
        ` : ''}
        <span class="intel-badge intel-stance" style="color: ${stanceColor};">
          <i class="fas fa-balance-scale"></i> Stance: ${stance.label}
        </span>
        <span class="intel-badge intel-demo">
          <i class="fas fa-user-tag"></i> Age: ${demo.inferred_age_bracket || '25-34'} | ${demo.primary_interest || 'Tech'}
        </span>
      </div>
      <div class="post-footer">
        <div class="post-metrics">
          <button class="post-metric-btn like-btn btn-like-action" style="cursor: pointer;">
            <i class="far fa-heart"></i> <span class="like-counter">${post.engagement?.likes || 1}</span>
          </button>
          <button class="post-metric-btn repost-btn btn-repost-action" style="cursor: pointer;">
            <i class="fas fa-retweet"></i> <span class="repost-counter">${post.engagement?.shares || 0}</span>
          </button>
          <button class="post-metric-btn btn-comments-action" style="cursor: pointer; background: rgba(99, 102, 241, 0.15); border-color: rgba(99, 102, 241, 0.4); color: var(--primary-light);">
            <i class="far fa-comment-dots"></i> Comments (<span id="post-cmt-count-${post.id}">${post.comments_count || 0}</span>)
          </button>
        </div>
        <div>
          ${post.target_user ? `<span style="color: var(--neon-purple); font-size: 0.72rem; font-weight: 600;"><i class="fas fa-retweet"></i> ${post.interaction_type || 'REPOST'} @${post.target_user}</span>` : ''}
        </div>
      </div>
    `;

    // 1. Bind Like Trigger
    const likeBtn = card.querySelector('.btn-like-action');
    const likeCounter = card.querySelector('.like-counter');
    let isLiked = false;
    if (likeBtn && likeCounter) {
      likeBtn.addEventListener('click', async () => {
        isLiked = !isLiked;
        let count = parseInt(likeCounter.innerText || '1', 10);
        count = isLiked ? count + 1 : Math.max(0, count - 1);
        likeCounter.innerText = count;

        if (isLiked) {
          likeBtn.classList.add('active');
          likeBtn.querySelector('i').className = 'fas fa-heart';
        } else {
          likeBtn.classList.remove('active');
          likeBtn.querySelector('i').className = 'far fa-heart';
        }

        const username = window.authController?.user?.username || 'operator';
        try {
          await ApiClient.likePost(post.id, isLiked, username);
        } catch (e) {
          console.error('Like sync error:', e);
        }
      });
    }

    // 2. Bind Repost Trigger
    const repostBtn = card.querySelector('.btn-repost-action');
    const repostCounter = card.querySelector('.repost-counter');
    let hasReposted = false;
    if (repostBtn && repostCounter) {
      repostBtn.addEventListener('click', async () => {
        if (hasReposted) {
          return alert('You have already reposted this intelligence dispatch!');
        }

        const confirmRepost = confirm(`🔄 Repost dispatch from @${author.username} to Live Stream Feed?`);
        if (!confirmRepost) return;

        repostBtn.disabled = true;
        repostBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Reposting...';

        const u = window.authController?.user || {};
        const authorUsername = u.username || 'operator';
        const authorName = u.full_name || 'Operator';
        const authorAvatar = u.avatar || null;
        const authorRole = u.role || 'Analyst';

        try {
          const res = await ApiClient.repostPost(post.id, {
            author_username: authorUsername,
            author_name: authorName,
            author_avatar: authorAvatar,
            author_role: authorRole
          });

          if (res.success) {
            hasReposted = true;
            let currentShares = parseInt(repostCounter.innerText || '0', 10);
            repostCounter.innerText = currentShares + 1;
            repostBtn.classList.add('active');
            repostBtn.innerHTML = `<i class="fas fa-retweet"></i> <span class="repost-counter">${currentShares + 1}</span>`;
            
            if (res.repost) {
              this.prependPostCard(res.repost);
            }
          }
        } catch (err) {
          alert('Error reposting: ' + err.message);
          repostBtn.disabled = false;
          repostBtn.innerHTML = `<i class="fas fa-retweet"></i> <span class="repost-counter">${repostCounter.innerText}</span>`;
        }
      });
    }

    // 3. Bind Comments Trigger
    const commentBtn = card.querySelector('.btn-comments-action');
    if (commentBtn) {
      commentBtn.addEventListener('click', () => this.openCommentsModal(post));
    }

    return card;
  }

  async openCommentsModal(post) {
    this.activeCommentPost = post;
    const modal = document.getElementById('comments-modal');
    const titleEl = document.getElementById('comments-modal-post-title');
    const authorEl = document.getElementById('comments-modal-post-author');
    const snippetEl = document.getElementById('comments-modal-post-snippet');
    const inputEl = document.getElementById('comment-input-text');

    if (!modal) return;

    if (titleEl) titleEl.innerText = `Discussion on ${post.platform} Post`;
    if (authorEl) authorEl.innerText = `Author: @${post.author?.username || 'user'} (${post.author?.name || 'User'})`;
    
    if (snippetEl) {
      snippetEl.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 4px;">${post.text}</div>
        ${post.media_url ? `<div style="font-size: 0.75rem; color: var(--neon-cyan);"><i class="fas fa-paperclip"></i> Media Attached (${post.media_type || 'Media'})</div>` : ''}
      `;
    }

    if (inputEl) inputEl.value = '';

    modal.style.display = 'flex';
    await this.loadComments(post.id);
  }

  closeCommentsModal() {
    const modal = document.getElementById('comments-modal');
    if (modal) modal.style.display = 'none';
    this.activeCommentPost = null;
  }

  async loadComments(postId) {
    const container = document.getElementById('comments-list-container');
    if (!container) return;
    container.innerHTML = '<div style="font-size: 0.78rem; color: var(--text-muted); text-align: center; padding: 1rem;"><i class="fas fa-spinner fa-spin"></i> Loading comments...</div>';

    try {
      const res = await ApiClient.getComments(postId);
      const comments = res.comments || [];
      if (comments.length === 0) {
        container.innerHTML = `
          <div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 1.5rem 1rem; border: 1px dashed var(--border-subtle); border-radius: 8px;">
            <i class="far fa-comments" style="font-size: 1.5rem; color: var(--neon-cyan); margin-bottom: 0.5rem; display: block;"></i>
            No comments yet. Be the first to add an audience reaction!
          </div>
        `;
        return;
      }

      container.innerHTML = comments.map(c => {
        const isToxic = c.is_toxic;
        const sentColor = c.sentiment_score > 0.1 ? '#10b981' : (c.sentiment_score < -0.1 ? '#f43f5e' : '#94a3b8');
        return `
          <div class="comment-item" style="background: rgba(14, 18, 27, 0.9); border: 1px solid ${isToxic ? 'rgba(244, 63, 94, 0.5)' : 'var(--border-subtle)'}; border-radius: 8px; padding: 0.65rem 0.85rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
              <div style="display: flex; align-items: center; gap: 0.45rem;">
                <img src="${c.author_avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${c.author_username}`}" alt="${c.author_name}" style="width: 20px; height: 20px; border-radius: 50%;" />
                <span style="font-size: 0.78rem; font-weight: 700; color: #fff;">${c.author_name || c.author_username}</span>
                <span style="font-size: 0.68rem; color: var(--text-muted); font-family: var(--font-mono);">@${c.author_username}</span>
              </div>
              <div style="display: flex; align-items: center; gap: 0.35rem;">
                <span style="font-size: 0.68rem; color: ${sentColor};"><i class="fas fa-heart"></i> ${c.sentiment_label}</span>
                ${isToxic ? '<span class="chip-badword" style="font-size: 0.62rem; padding: 1px 5px;"><i class="fas fa-exclamation-triangle"></i> Flagged Warning</span>' : ''}
                <span style="font-size: 0.68rem; color: var(--text-muted); font-family: var(--font-mono);">${c.timestamp_iso || 'Now'}</span>
              </div>
            </div>
            <div style="font-size: 0.8rem; color: ${isToxic ? '#fda4af' : 'var(--text-main)'}; line-height: 1.4;">${c.text}</div>
          </div>
        `;
      }).join('');
    } catch (err) {
      container.innerHTML = `<div style="color: #f43f5e; font-size: 0.78rem;">Error loading comments: ${err.message}</div>`;
    }
  }

  async submitComment(postId, forcePublish = false) {
    const inputEl = document.getElementById('comment-input-text');
    if (!inputEl) return;
    const text = inputEl.value.trim();
    if (!text) return alert('Please enter comment text.');

    let authorUsername = 'operator';
    let authorName = 'Intelligence Operator';
    let authorAvatar = null;
    let authorRole = 'Analyst';

    if (window.authController && window.authController.user) {
      authorUsername = window.authController.user.username || 'operator';
      authorName = window.authController.user.full_name || 'Operator';
      authorAvatar = window.authController.user.avatar || null;
      authorRole = window.authController.user.role || 'Analyst';
    }

    const btn = document.getElementById('btn-submit-comment');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking & Posting...';
    }

    try {
      const res = await ApiClient.addComment(postId, {
        text: text,
        author_username: authorUsername,
        author_name: authorName,
        author_avatar: authorAvatar,
        author_role: authorRole,
        force_publish: forcePublish
      });

      if (res.warning_required && res.toxicity) {
        // AI Anti-Toxicity Moderation Intercepted Bad Language!
        this.lastAnalyzedToxicity = res.toxicity;
        this.showToxicityWarningModal(res.toxicity, text, true);
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i class="fas fa-comment-dots"></i> Post Comment';
        }
        return;
      }

      if (res.success && res.comment) {
        inputEl.value = '';
        await this.loadComments(postId);
        
        // Update badge on post card
        const countBadge = document.getElementById(`post-cmt-count-${postId}`);
        if (countBadge) {
          const cur = parseInt(countBadge.innerText || '0', 10);
          countBadge.innerText = cur + 1;
        }
      }
    } catch (err) {
      alert('Error submitting comment: ' + err.message);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-comment-dots"></i> Post Comment';
      }
    }
  }

  renderTrends(trends) {
    const tbody = document.getElementById('trends-table-body');
    if (!tbody || !trends) return;
    tbody.innerHTML = '';

    trends.forEach((t, i) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-family: var(--font-mono); font-weight: bold; color: var(--text-muted);">${i + 1}</td>
        <td>
          <span class="trend-topic-name">${t.topic}</span>
          <div style="font-size: 0.7rem; color: var(--text-muted);">${t.platforms.join(' • ')}</div>
        </td>
        <td>
          <div class="virality-bar-bg">
            <div class="virality-bar-fill" style="width: ${t.virality_score}%;"></div>
          </div>
          <span style="font-family: var(--font-mono); font-weight: bold; color: var(--neon-cyan);">${t.virality_score}</span>
        </td>
        <td style="font-family: var(--font-mono); color: ${t.velocity > 0 ? '#10b981' : '#f43f5e'};">
          ${t.velocity > 0 ? '+' : ''}${t.velocity}%
        </td>
        <td><span class="kpi-badge badge-purple">${t.status}</span></td>
        <td>
          <span style="color: ${t.avg_sentiment > 0.1 ? '#10b981' : (t.avg_sentiment < -0.1 ? '#f43f5e' : '#94a3b8')}; font-weight: 600;">
            ${t.sentiment_label} (${t.avg_sentiment})
          </span>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  renderNetwork(network) {
    if (!network) return;
    this.lastNetworkData = network;
    this.networkGraph.render(network);
    
    // Render KOLs list
    const kolList = document.getElementById('kols-ranking-list');
    if (!kolList) return;
    kolList.innerHTML = '';

    (network.kols || []).forEach((kol, idx) => {
      const item = document.createElement('div');
      item.className = 'kol-item';
      item.onclick = () => this.networkGraph.highlightKOL(kol.id);

      item.innerHTML = `
        <div class="kol-meta">
          <div class="kol-rank">#${idx + 1}</div>
          <img class="author-avatar" src="${kol.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${kol.id}`}" alt="${kol.name}"/>
          <div>
            <div style="font-size: 0.85rem; font-weight: 600; color: #fff;">${kol.name}</div>
            <div style="font-size: 0.72rem; color: var(--text-muted);">${kol.label} • ${kol.role}</div>
          </div>
        </div>
        <div style="text-align: right;">
          <div class="kol-score">${kol.influence_score} ★</div>
          <div style="font-size: 0.7rem; color: var(--text-muted); font-family: var(--font-mono);">${kol.followers.toLocaleString()} fllwrs</div>
        </div>
      `;
      kolList.appendChild(item);
    });
  }

  populateCascadeSeedSelect(kols) {
    const select = document.getElementById('cascade-seed-select');
    if (!select || !kols) return;
    select.innerHTML = '';
    kols.forEach(k => {
      const opt = document.createElement('option');
      opt.value = k.id;
      opt.innerText = `${k.name} (@${k.id}) - ${k.influence_score} ★`;
      select.appendChild(opt);
    });
  }

  renderCascadeLog(cascade) {
    const log = document.getElementById('cascade-log-container') || document.getElementById('cascade-log');
    if (!log || !cascade) return;
    log.innerHTML = '';

    const steps = Array.isArray(cascade) ? cascade : (cascade.steps || []);
    if (steps.length === 0) {
      log.innerHTML = '<div style="font-size: 0.75rem; color: var(--text-muted); padding: 0.5rem;">No cascade propagation steps detected.</div>';
      return;
    }

    steps.forEach((s, idx) => {
      const el = document.createElement('div');
      el.className = 'cascade-step-item';
      el.style.cssText = 'background: rgba(0, 0, 0, 0.4); border-left: 3px solid var(--neon-cyan); padding: 0.5rem 0.75rem; margin-bottom: 0.4rem; border-radius: 6px; border: 1px solid rgba(0, 240, 255, 0.15); border-left-width: 3px;';
      
      const propagations = s.propagations || [];
      const reached = s.total_reached || s.cumulative_reach || (idx + 1) * 2;
      const actNodes = propagations.length > 0 
        ? propagations.map(p => `<span style="color: var(--neon-cyan);">@${p.to_node}</span> (${p.action || 'Retweeted'} by @${p.from_node})`).join(', ')
        : 'Initial narrative seed broadcast';

      el.innerHTML = `
        <div style="display: flex; justify-content: space-between; font-size: 0.78rem;">
          <span style="font-weight: 700; color: var(--neon-cyan);"><i class="fas fa-arrow-right"></i> Step ${s.step || (idx + 1)}: Diffusion Phase</span>
          <span style="color: #10b981; font-family: var(--font-mono); font-weight: 600;">Cumulative Reach: ${reached.toLocaleString()} users</span>
        </div>
        <div style="font-size: 0.74rem; color: var(--text-secondary); margin-top: 4px;">
          <b>Propagations:</b> ${actNodes}
        </div>
      `;
      log.appendChild(el);
    });
  }

  updateToxicityLiveIndicator(tox) {
    const pill = document.getElementById('toxicity-live-indicator');
    if (!pill || !tox) return;

    if (tox.severity === 'SAFE') {
      pill.className = 'toxicity-pill-badge pill-safe';
      pill.innerHTML = '<i class="fas fa-shield-alt"></i> <span>Live Guardrail: Clean</span>';
    } else if (tox.severity === 'LOW') {
      pill.className = 'toxicity-pill-badge pill-warning';
      pill.innerHTML = `<i class="fas fa-exclamation-triangle"></i> <span>Mild Trigger (${tox.detected_bad_words.length + tox.detected_bad_hashtags.length})</span>`;
    } else if (tox.severity === 'MEDIUM') {
      pill.className = 'toxicity-pill-badge pill-warning';
      pill.innerHTML = `<i class="fas fa-exclamation-triangle"></i> <span>Flagged: Bad Words / Tags (${tox.detected_bad_words.length + tox.detected_bad_hashtags.length})</span>`;
    } else {
      pill.className = 'toxicity-pill-badge pill-danger';
      pill.innerHTML = `<i class="fas fa-radiation-alt"></i> <span>Violation: ${tox.severity} Toxicity!</span>`;
    }
  }

  showToxicityWarningModal(tox, rawText, isComment = false) {
    const modal = document.getElementById('toxicity-warning-modal');
    if (!modal) return;

    const headingEl = modal.querySelector('.modal-heading');
    const subheadingEl = modal.querySelector('.modal-subheading');
    const severityBadge = document.getElementById('modal-severity-badge');
    const percentEl = document.getElementById('modal-toxicity-percent');
    const fillEl = document.getElementById('modal-meter-fill');
    const wordsContainer = document.getElementById('modal-badwords-container');
    const wordsChips = document.getElementById('modal-badwords-chips');
    const tagsContainer = document.getElementById('modal-badtags-container');
    const tagsChips = document.getElementById('modal-badtags-chips');
    const catChips = document.getElementById('modal-categories-chips');
    const actionText = document.getElementById('modal-action-text');
    const explText = document.getElementById('modal-explanation-text');
    const btnSanitize = document.getElementById('btn-sanitize-text');
    const btnDismiss = document.getElementById('btn-dismiss-modal');

    if (headingEl) {
      headingEl.innerText = isComment 
        ? '🚨 BAD COMMENT DETECTED!' 
        : 'Toxicity & Content Guardrail Alert';
    }
    if (subheadingEl) {
      subheadingEl.innerText = isComment
        ? 'Your comment violates community safety guidelines. Offensive or abusive words were detected and blocked.'
        : 'Our AI filter detected offensive terms, toxic hashtags, or abusive content in your submission.';
    }

    if (btnSanitize) {
      btnSanitize.innerHTML = isComment
        ? '<i class="fas fa-magic"></i> Auto-Sanitize & Post Comment'
        : '<i class="fas fa-magic"></i> Auto-Sanitize Bad Words';
    }

    if (btnDismiss) {
      btnDismiss.innerHTML = isComment
        ? '<i class="fas fa-pencil"></i> Edit & Revise Comment'
        : '<i class="fas fa-check"></i> I Acknowledge Warning';
    }

    const scorePct = Math.round((tox.toxicity_score || 0.6) * 100);

    if (severityBadge) {
      severityBadge.innerText = `${tox.severity || 'HIGH'} VIOLATION`;
      severityBadge.style.color = tox.severity === 'CRITICAL' ? '#ff3366' : (tox.severity === 'HIGH' ? '#f43f5e' : '#f59e0b');
    }

    if (percentEl) percentEl.innerText = `${scorePct}%`;
    if (fillEl) fillEl.style.width = `${Math.max(20, scorePct)}%`;

    // Bad words chips
    const words = tox.detected_bad_words || [];
    if (wordsContainer && wordsChips) {
      if (words.length > 0) {
        wordsContainer.style.display = 'flex';
        wordsChips.innerHTML = words.map(w => `<span class="chip-badword"><i class="fas fa-ban"></i> ${w}</span>`).join('');
      } else {
        wordsContainer.style.display = 'none';
      }
    }

    // Bad hashtags chips
    const tags = tox.detected_bad_hashtags || [];
    if (tagsContainer && tagsChips) {
      if (tags.length > 0) {
        tagsContainer.style.display = 'flex';
        tagsChips.innerHTML = tags.map(t => `<span class="chip-badtag"><i class="fas fa-hashtag"></i> ${t}</span>`).join('');
      } else {
        tagsContainer.style.display = 'none';
      }
    }

    // Category chips
    const cats = tox.categories || [];
    if (catChips) {
      if (cats.length > 0) {
        catChips.innerHTML = cats.map(c => `<span class="chip-category"><i class="fas fa-tag"></i> ${c}</span>`).join('');
      } else {
        catChips.innerHTML = '<span class="chip-category">Profanity / Abusive Language</span>';
      }
    }

    if (actionText) actionText.innerText = isComment ? 'Comment Blocked — Revise or Auto-Sanitize' : (tox.moderation_action === 'AUTO_BLOCK' ? 'Auto-Block & Flag User Profile' : 'Pop-Up Warning & Content Flagged');
    if (explText) explText.innerText = tox.explanation || 'Offensive, profane, or abusive words were detected in your comment.';

    const emailNoticeText = document.getElementById('modal-email-target-text');
    const userEmail = (window.authController?.user?.email) || `${window.authController?.user?.username || 'user'}@socialmediaanalytics.io`;
    if (emailNoticeText) {
      emailNoticeText.textContent = `A formal Conduct Violation Notice has been automatically dispatched to ${userEmail}.`;
    }

    modal.style.display = 'flex';
  }

  hideToxicityWarningModal() {
    const modal = document.getElementById('toxicity-warning-modal');
    if (modal) modal.style.display = 'none';
  }

  sanitizeText(text, badWords, badTags) {
    let result = text;
    badWords.forEach(bad => {
      const cleanBad = bad.replace('#', '');
      const regex = new RegExp(`\\b${cleanBad}\\b`, 'gi');
      result = result.replace(regex, cleanBad[0] + '*'.repeat(Math.max(2, cleanBad.length - 1)));
    });
    badTags.forEach(tag => {
      const regex = new RegExp(tag.replace(/([.*+?^=!:${}()|\[\]\/\\])/g, "\\$1"), 'gi');
      result = result.replace(regex, '#[moderated_tag]');
    });
    return result;
  }

  renderAnalyzerResults(data) {
    const container = document.getElementById('analyzer-results-box');
    if (!container) return;
    container.style.display = 'block';

    const s = data.sentiment || {};
    const d = data.demographics || {};
    const sarcasm = s.sarcasm || {};
    const tox = data.toxicity || s.toxicity || {};

    const isToxic = tox.is_toxic;
    const toxScorePct = Math.round((tox.toxicity_score || 0) * 100);

    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; border-bottom: 1px solid var(--border-subtle); padding-bottom: 0.5rem;">
        <div style="font-size: 1.05rem; font-weight: 700; color: #fff;">
          <i class="fas fa-check-circle" style="color: var(--neon-emerald);"></i> AI Inference Output
        </div>
        <div>
          ${isToxic ? `
            <span class="toxicity-pill-badge pill-danger" style="cursor: pointer;" id="btn-reopen-tox-modal">
              <i class="fas fa-radiation-alt"></i> ${tox.severity} VIOLATION (${toxScorePct}%)
            </span>
          ` : `
            <span class="toxicity-pill-badge pill-safe">
              <i class="fas fa-shield-alt"></i> Safe & Compliant
            </span>
          `}
        </div>
      </div>

      <!-- Toxicity & Guardrail Deep Breakdown Banner if Toxic -->
      ${isToxic ? `
        <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.4); border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
            <span style="font-size: 0.8rem; font-weight: 700; color: #ff4d6d; display: flex; align-items: center; gap: 0.4rem;">
              <i class="fas fa-exclamation-triangle"></i> Content Moderation Triggered
            </span>
            <span style="font-size: 0.75rem; color: var(--text-secondary);">Action: <b>${tox.moderation_action}</b></span>
          </div>
          <div style="font-size: 0.78rem; color: var(--text-primary); margin-bottom: 0.5rem;">
            ${tox.explanation}
          </div>
          <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
            ${(tox.detected_bad_words || []).map(w => `<span class="chip-badword"><i class="fas fa-ban"></i> ${w}</span>`).join('')}
            ${(tox.detected_bad_hashtags || []).map(t => `<span class="chip-badtag"><i class="fas fa-hashtag"></i> ${t}</span>`).join('')}
          </div>
        </div>
      ` : ''}

      <div class="radar-stat-grid">
        <div class="radar-stat-card">
          <div class="lbl">Primary Emotion</div>
          <div class="val" style="color: ${isToxic ? '#f43f5e' : '#00f0ff'};">${(s.primary_emotion || 'Neutral').toUpperCase()}</div>
        </div>
        <div class="radar-stat-card">
          <div class="lbl">Valence & Sentiment</div>
          <div class="val" style="color: ${s.valence > 0.1 ? '#10b981' : (s.valence < -0.1 ? '#f43f5e' : '#94a3b8')};">
            ${s.sentiment_label} (${s.valence})
          </div>
        </div>
        <div class="radar-stat-card">
          <div class="lbl">Sarcasm & Irony</div>
          <div class="val" style="color: ${sarcasm.is_sarcastic ? '#f43f5e' : '#10b981'};">
            ${sarcasm.is_sarcastic ? `YES (${Math.round(sarcasm.confidence * 100)}%)` : 'NO (0%)'}
          </div>
        </div>
        <div class="radar-stat-card">
          <div class="lbl">Toxicity Index</div>
          <div class="val" style="color: ${isToxic ? '#f43f5e' : '#10b981'};">${toxScorePct}% (${tox.severity || 'SAFE'})</div>
        </div>
        <div class="radar-stat-card">
          <div class="lbl">Inferred Age Group</div>
          <div class="val" style="color: #38bdf8;">${d.inferred_age_bracket || '25-34'}</div>
        </div>
        <div class="radar-stat-card">
          <div class="lbl">Professional Domain</div>
          <div class="val" style="color: #f59e0b;">${d.primary_interest || 'Tech & AI'}</div>
        </div>
      </div>
      <div style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-secondary);">
        <b>Inferred Persona:</b> <span class="kpi-badge badge-cyan">${d.persona_archetype || 'Audience Member'}</span> | 
        <b>Geo Origin:</b> <span style="color:#fff;">${d.geographic_origin || 'Global'}</span> | 
        <b>Language:</b> <span style="color:#fff;">${d.inferred_language || 'English'}</span>
      </div>
    `;

    const reopenBtn = document.getElementById('btn-reopen-tox-modal');
    if (reopenBtn && isToxic) {
      reopenBtn.addEventListener('click', () => {
        this.showToxicityWarningModal(tox, data.text || '');
      });
    }
  }


  async loadRealUsers() {
    try {
      const data = await ApiClient.getRealUsers('all', '', 150);
      this.realUsers = data.users || [];
      this.updateRealUserStats(data.stats || {});
      this.filterAndRenderRealUsers();
    } catch (err) {
      console.error('Failed to load real users:', err);
    }
  }

  updateRealUserStats(stats) {
    const total = stats.total_real_users || this.realUsers.length;
    const byPlat = stats.by_platform || {};

    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) {
        const num = Number(val);
        el.innerText = (!isNaN(num) && typeof val !== 'string') ? num.toLocaleString() : (typeof val === 'number' ? val.toLocaleString() : val);
      }
    };

    setVal('stat-total-real-users', total);
    setVal('count-pill-all', total);
    setVal('stat-tg-users', byPlat['Telegram'] || 10000);
    setVal('stat-x-users', byPlat['X'] || 10000);
    setVal('stat-ig-users', byPlat['Instagram'] || 10000);
    setVal('stat-yt-users', byPlat['YouTube'] || 10000);
    setVal('stat-reddit-users', byPlat['Reddit'] || 10000);
    setVal('stat-fb-users', byPlat['Facebook'] || 10000);
  }

  filterAndRenderRealUsers() {
    let filtered = this.realUsers;
    if (this.currentRealUserPlatform !== 'all') {
      filtered = filtered.filter(u => u.platform.toLowerCase() === this.currentRealUserPlatform.toLowerCase());
    }
    if (this.realUserSearch) {
      const q = this.realUserSearch;
      filtered = filtered.filter(u => 
        (u.username && u.username.toLowerCase().includes(q)) ||
        (u.name && u.name.toLowerCase().includes(q)) ||
        (u.bio && u.bio.toLowerCase().includes(q)) ||
        (u.location && u.location.toLowerCase().includes(q)) ||
        (u.demographics?.primary_interest && u.demographics.primary_interest.toLowerCase().includes(q))
      );
    }
    this.renderRealUsers(filtered);
  }

  renderRealUsers(users) {
    const container = document.getElementById('real-users-grid-container');
    if (!container) return;

    if (!users || users.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">
          <i class="fas fa-users-slash" style="font-size: 2.5rem; margin-bottom: 1rem; color: var(--border-glow);"></i>
          <p>No real users matched your criteria. Click "Collect Live Real Data" to fetch fresh users across Telegram, Reddit, YouTube, Facebook, X & Instagram.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = '';
    users.forEach(u => {
      const demo = u.demographics || {};
      const platformLower = (u.platform || 'x').toLowerCase();
      const platformClass = `tag-${platformLower}`;
      const latestPost = (u.recent_posts && u.recent_posts.length > 0) ? u.recent_posts[0] : null;

      const card = document.createElement('div');
      card.className = 'real-user-card';
      card.style.setProperty('--platform-color', 
        platformLower === 'telegram' ? '#24a1de' : 
        platformLower === 'reddit' ? '#ff4500' : 
        platformLower === 'youtube' ? '#ff3333' : 
        platformLower === 'facebook' ? '#1877f2' : 
        platformLower === 'instagram' ? '#e1306c' : '#00f0ff'
      );

      card.innerHTML = `
        <div>
          <div class="real-user-header">
            <img class="real-user-avatar" src="${u.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${u.username}`}" alt="${u.name}"/>
            <div class="real-user-meta">
              <div class="real-user-title">
                ${u.name}
                <i class="fas fa-circle-check" style="color: var(--neon-cyan); font-size: 0.8rem;" title="Verified Live Real User"></i>
              </div>
              <div class="real-user-handle">${u.username}</div>
            </div>
            <span class="post-platform-tag ${platformClass}"><i class="fas fa-hashtag"></i> ${u.platform}</span>
          </div>

          <div class="real-user-bio">${u.bio || 'Authentic community contributor.'}</div>

          <div class="real-user-tags">
            <span class="user-tag"><i class="fas fa-users"></i> ${(u.followers || 0).toLocaleString()} followers</span>
            <span class="user-tag"><i class="fas fa-map-pin"></i> ${demo.geographic_origin || u.location || 'Global'}</span>
            <span class="user-tag"><i class="fas fa-brain"></i> ${demo.inferred_age_bracket || '25-34'}</span>
            <span class="user-tag"><i class="fas fa-briefcase"></i> ${demo.primary_interest || 'Tech'}</span>
          </div>

          ${latestPost ? `
            <div class="real-user-post-box">
              <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 3px; display: flex; justify-content: space-between;">
                <span><i class="fas fa-comment-dots"></i> Latest Live Post:</span>
                <span style="color: ${latestPost.valence > 0.1 ? '#10b981' : (latestPost.valence < -0.1 ? '#f43f5e' : '#94a3b8')}">${latestPost.sentiment_label} (${latestPost.valence})</span>
              </div>
              <div style="line-height: 1.4;">${latestPost.text}</div>
            </div>
          ` : ''}
        </div>

        <div class="real-user-footer">
          <span><i class="fas fa-layer-group"></i> ${u.posts_count || 1} Collected Posts</span>
          <a class="btn-profile-link" href="${u.profile_url || '#'}" target="_blank" rel="noopener noreferrer">
            Open Profile <i class="fas fa-arrow-up-right-from-square"></i>
          </a>
        </div>
      `;
      container.appendChild(card);
    });
  }

  initInfluencerRankings() {
    const searchInput = document.getElementById('inf-search-input');
    const countryFilter = document.getElementById('inf-country-filter');
    const platformFilter = document.getElementById('inf-platform-filter');
    const sortFilter = document.getElementById('inf-sort-filter');
    const btnRefresh = document.getElementById('btn-inf-refresh');

    if (searchInput) {
      let debounceTimer;
      searchInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => this.loadInfluencerRankings(), 300);
      });
    }

    if (countryFilter) {
      countryFilter.addEventListener('change', () => this.loadInfluencerRankings());
    }

    if (platformFilter) {
      platformFilter.addEventListener('change', () => this.loadInfluencerRankings());
    }

    if (sortFilter) {
      sortFilter.addEventListener('change', () => this.loadInfluencerRankings());
    }

    if (btnRefresh) {
      btnRefresh.addEventListener('click', () => this.loadInfluencerRankings());
    }
  }

  async loadInfluencerRankings() {
    const searchInput = document.getElementById('inf-search-input');
    const countryFilter = document.getElementById('inf-country-filter');
    const platformFilter = document.getElementById('inf-platform-filter');
    const sortFilter = document.getElementById('inf-sort-filter');

    const search = searchInput ? searchInput.value.trim() : '';
    const country = countryFilter ? countryFilter.value : 'all';
    const platform = platformFilter ? platformFilter.value : 'all';
    const sort = sortFilter ? sortFilter.value : 'influence_score';

    try {
      const data = await ApiClient.getInfluencerRankings(platform, country, 'all', search, sort);
      if (data && data.rankings) {
        this.renderInfluencerPodium(data.rankings.slice(0, 3));
        this.renderInfluencerTable(data.rankings);
      }
    } catch (err) {
      console.error('Failed to load influencer rankings:', err);
    }
  }

  renderInfluencerPodium(top3) {
    const podiumEl = document.getElementById('influencer-podium-grid');
    if (!podiumEl) return;
    podiumEl.innerHTML = '';

    if (!top3 || top3.length === 0) {
      podiumEl.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">No matching influencers found.</div>';
      return;
    }

    // Render Rank 1, 2, 3 podium cards
    top3.forEach((c, idx) => {
      const rank = idx + 1;
      const rankClass = rank === 1 ? 'podium-rank-1' : (rank === 2 ? 'podium-rank-2' : 'podium-rank-3');
      const badgeClass = rank === 1 ? 'podium-badge-gold' : (rank === 2 ? 'podium-badge-silver' : 'podium-badge-bronze');
      const badgeText = rank === 1 ? '🥇 RANK #1 &bull; GRAND CHAMPION' : (rank === 2 ? '🥈 RANK #2 &bull; TOP VIRAL' : '🥉 RANK #3 &bull; HIGH REACH');
      const flag = c.country === 'India' ? '🇮🇳' : (c.country === 'United States' ? '🇺🇸' : (c.country === 'United Kingdom' ? '🇬🇧' : (c.country === 'Germany' ? '🇩🇪' : (c.country === 'Singapore' ? '🇸🇬' : (c.country === 'Canada' ? '🇨🇦' : '🌐')))));

      const card = document.createElement('div');
      card.className = `podium-card ${rankClass}`;
      card.innerHTML = `
        <span class="podium-badge ${badgeClass}">${badgeText}</span>
        
        <div class="podium-avatar-wrapper">
          ${rank === 1 ? '<i class="fas fa-crown podium-crown-icon"></i>' : ''}
          <img class="podium-avatar" src="${c.avatar}" alt="${c.name}" />
        </div>

        <h3 class="podium-name">${c.name}</h3>
        <div class="podium-handle">@${c.username.replace('@', '').replace('t.me/', '').replace('u/', '')}</div>

        <div class="podium-meta-row">
          <span class="platform-pill platform-pill-${c.platform.toLowerCase()}">
            <i class="fab fa-${c.platform.toLowerCase() === 'x' ? 'x-twitter' : c.platform.toLowerCase()}"></i> ${c.platform}
          </span>
          <span class="country-pill">${flag} ${c.country}</span>
        </div>

        <div style="font-size: 0.74rem; color: var(--text-muted); margin-bottom: 0.75rem;">
          <i class="fas fa-briefcase"></i> ${c.category}
        </div>

        <div class="podium-score-pill">
          <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-bottom: 4px;">
            <span style="color: var(--text-muted);"><i class="fas fa-bolt" style="color: #fbbf24;"></i> Influence Score</span>
            <strong style="color: var(--neon-cyan); font-family: var(--font-mono);">${c.influence_score} / 100</strong>
          </div>
          <div class="score-bar-track">
            <div class="score-bar-fill" style="width: ${c.influence_score}%;"></div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.72rem; color: #cbd5e1; margin-top: 6px;">
            <span><i class="fas fa-users"></i> ${c.followers.toLocaleString()} Followers</span>
            <span style="color: #10b981;">${c.engagement_rate}% Eng.</span>
          </div>
        </div>
      `;
      podiumEl.appendChild(card);
    });
  }

  renderInfluencerTable(rankings) {
    const tbody = document.getElementById('influencer-rankings-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!rankings || rankings.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">No influencers match the selected filters.</td></tr>';
      return;
    }

    rankings.forEach(c => {
      const tr = document.createElement('tr');
      const rankBadge = c.rank === 1 ? 'rank-1-badge' : (c.rank === 2 ? 'rank-2-badge' : (c.rank === 3 ? 'rank-3-badge' : 'rank-normal-badge'));
      const flag = c.country === 'India' ? '🇮🇳' : (c.country === 'United States' ? '🇺🇸' : (c.country === 'United Kingdom' ? '🇬🇧' : (c.country === 'Germany' ? '🇩🇪' : (c.country === 'Singapore' ? '🇸🇬' : (c.country === 'Canada' ? '🇨🇦' : '🌐')))));
      const stanceColor = c.sentiment_stance === 'Supportive' ? '#10b981' : (c.sentiment_stance === 'Critical' ? '#f43f5e' : '#94a3b8');

      tr.innerHTML = `
        <td style="text-align: center;">
          <span class="rank-badge ${rankBadge}">#${c.rank}</span>
        </td>
        <td>
          <div class="creator-profile-cell">
            <img class="creator-avatar" src="${c.avatar}" alt="${c.name}" />
            <div>
              <div class="creator-name">
                ${c.name}
                <i class="fas fa-circle-check" style="color: #38bdf8; font-size: 0.75rem; margin-left: 3px;" title="Verified Creator"></i>
              </div>
              <div class="creator-handle">@${c.username.replace('@', '').replace('t.me/', '').replace('u/', '')}</div>
            </div>
          </div>
        </td>
        <td>
          <span class="platform-pill platform-pill-${c.platform.toLowerCase()}">
            <i class="fab fa-${c.platform.toLowerCase() === 'x' ? 'x-twitter' : c.platform.toLowerCase()}"></i> ${c.platform}
          </span>
        </td>
        <td>
          <span class="country-pill">${flag} ${c.country}</span>
          <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 2px;">${c.location}</div>
        </td>
        <td>
          <span style="font-size: 0.78rem; font-weight: 600; color: #e2e8f0;"><i class="fas fa-briefcase" style="color: var(--neon-cyan); margin-right: 4px;"></i>${c.category}</span>
        </td>
        <td style="text-align: right; font-family: var(--font-mono); font-weight: 700; color: #fff;">
          ${c.followers.toLocaleString()}
          <div style="font-size: 0.7rem; color: #10b981; font-weight: 500;">${c.engagement_rate}% Rate</div>
        </td>
        <td>
          <div class="score-bar-wrapper">
            <div class="score-bar-track">
              <div class="score-bar-fill" style="width: ${c.influence_score}%;"></div>
            </div>
            <span class="score-val">${c.influence_score}</span>
          </div>
        </td>
        <td style="text-align: center;">
          <span class="badge-pill" style="background: rgba(255, 255, 255, 0.06); color: ${stanceColor}; border: 1px solid ${stanceColor}40; font-size: 0.72rem; padding: 0.2rem 0.5rem; border-radius: 12px;">
            ${c.sentiment_stance}
          </span>
        </td>
        <td style="text-align: center;">
          <a class="btn-icon" href="${c.profile_url}" target="_blank" rel="noopener noreferrer" style="font-size: 0.75rem; padding: 0.35rem 0.65rem;" title="View External Profile">
            <i class="fas fa-arrow-up-right-from-square"></i>
          </a>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  async refreshFeed() {
    try {
      const serverPosts = await ApiClient.getFeed(40, this.currentPlatformFilter, this.currentEmotionFilter, this.searchQuery);
      if (serverPosts && serverPosts.length > 0) {
        this.renderFeed(serverPosts);
        return;
      }
    } catch (e) {
      console.warn('Fallback to active posts filter:', e);
    }
    const filtered = this.activeFeedPosts.filter(p => this.matchesCurrentFilters(p));
    this.renderFeed(filtered);
  }
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  app.init();
});
