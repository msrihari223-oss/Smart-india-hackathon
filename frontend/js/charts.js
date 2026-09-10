/**
 * Visual Intelligence Charts Manager (Chart.js Integration)
 */

export class ChartManager {
  constructor() {
    this.emotionChart = null;
    this.timelineChart = null;
    this.ageChart = null;
    this.interestChart = null;
    this.geoChart = null;
  }

  initEmotionDonut(canvasId, initialData = {}) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const ctx = el.getContext('2d');
    const labels = ['Joy', 'Excitement', 'Anxiety', 'Anger', 'Sadness', 'Supportive', 'Against', 'Neutral'];
    const colors = ['#10B981', '#00F0FF', '#F59E0B', '#EF4444', '#64748B', '#3B82F6', '#EC4899', '#94A3B8'];

    this.emotionChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: [25, 20, 15, 12, 8, 10, 5, 5],
          backgroundColor: colors,
          borderColor: '#07090e',
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#94a3b8', boxWidth: 12, padding: 12, font: { family: 'Outfit', size: 11 } }
          }
        }
      }
    });
  }

  updateEmotionDonut(distribution) {
    if (!this.emotionChart || !distribution) return;
    const mapping = {
      'Joy': distribution.joy || 0,
      'Excitement': distribution.excitement || 0,
      'Anxiety': distribution.anxiety || 0,
      'Anger': distribution.anger || 0,
      'Sadness': distribution.sadness || 0,
      'Supportive': distribution.supportive || 0,
      'Against': distribution.against || 0,
      'Neutral': distribution.neutral || 0
    };
    this.emotionChart.data.datasets[0].data = Object.values(mapping);
    this.emotionChart.update('none');
  }

  initTimelineChart(canvasId) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const ctx = el.getContext('2d');
    this.timelineChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: ['00:00', '00:05', '00:10', '00:15', '00:20', '00:25'],
        datasets: [
          {
            label: 'Sentiment Valence (-1 to +1)',
            data: [0.2, 0.45, -0.1, 0.3, 0.6, 0.15],
            borderColor: '#00f0ff',
            backgroundColor: 'rgba(0, 240, 255, 0.08)',
            fill: true,
            tension: 0.35,
            yAxisID: 'y',
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: '#00f0ff'
          },
          {
            label: 'Post Ingestion Volume',
            data: [12, 19, 15, 25, 30, 22],
            type: 'bar',
            backgroundColor: 'rgba(168, 85, 247, 0.25)',
            borderColor: 'rgba(168, 85, 247, 0.7)',
            borderWidth: 1,
            borderRadius: 4,
            yAxisID: 'y1'
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.04)' },
            ticks: { color: '#64748b', font: { family: 'Outfit', size: 10 } }
          },
          y: {
            type: 'linear',
            position: 'left',
            min: -1.0,
            max: 1.0,
            grid: { color: 'rgba(255,255,255,0.06)' },
            ticks: { color: '#00f0ff', font: { family: 'JetBrains Mono', size: 10 } }
          },
          y1: {
            type: 'linear',
            position: 'right',
            grid: { drawOnChartArea: false },
            ticks: { color: '#a855f7', font: { family: 'JetBrains Mono', size: 10 } }
          }
        },
        plugins: {
          legend: {
            labels: { color: '#94a3b8', boxWidth: 12, font: { family: 'Outfit', size: 11 } }
          }
        }
      }
    });
  }

  updateTimelineChart(timelineData) {
    if (!this.timelineChart || !timelineData) return;
    this.timelineChart.data.labels = timelineData.timestamps || [];
    this.timelineChart.data.datasets[0].data = timelineData.sentiment_series || [];
    this.timelineChart.data.datasets[1].data = timelineData.volume_series || [];
    this.timelineChart.update('none');
  }

  initAgeDistribution(canvasId) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const ctx = el.getContext('2d');
    this.ageChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['18-24', '25-34', '35-44', '45-54', '55+'],
        datasets: [{
          label: 'Follower %',
          data: [28, 44, 18, 7, 3],
          backgroundColor: [
            'rgba(0, 240, 255, 0.45)',
            'rgba(168, 85, 247, 0.45)',
            'rgba(16, 185, 129, 0.45)',
            'rgba(245, 158, 11, 0.45)',
            'rgba(236, 72, 153, 0.45)'
          ],
          borderColor: ['#00f0ff', '#a855f7', '#10b981', '#f59e0b', '#ec4899'],
          borderWidth: 1,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  updateAgeDistribution(ageData) {
    if (!this.ageChart || !ageData) return;
    this.ageChart.data.labels = Object.keys(ageData);
    this.ageChart.data.datasets[0].data = Object.values(ageData);
    this.ageChart.update('none');
  }

  initInterestsRadar(canvasId) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const ctx = el.getContext('2d');
    this.interestChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['Tech & AI', 'Finance', 'BioTech', 'Policy', 'Media', 'Research', 'Gaming'],
        datasets: [{
          label: 'Domain Affinity',
          data: [85, 65, 40, 50, 60, 45, 70],
          backgroundColor: 'rgba(168, 85, 247, 0.2)',
          borderColor: '#a855f7',
          pointBackgroundColor: '#00f0ff',
          pointBorderColor: '#fff',
          pointRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            angleLines: { color: 'rgba(255,255,255,0.08)' },
            grid: { color: 'rgba(255,255,255,0.08)' },
            pointLabels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } },
            ticks: { display: false }
          }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  updateInterestsRadar(interestData) {
    if (!this.interestChart || !interestData) return;
    this.interestChart.data.labels = Object.keys(interestData);
    this.interestChart.data.datasets[0].data = Object.values(interestData);
    this.interestChart.update('none');
  }

  initGeoChart(canvasId) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const ctx = el.getContext('2d');
    this.geoChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['USA', 'India', 'UK', 'Germany', 'Canada', 'Singapore'],
        datasets: [{
          label: 'Geographic Volume',
          data: [35, 28, 14, 9, 7, 7],
          backgroundColor: 'rgba(0, 240, 255, 0.35)',
          borderColor: '#00f0ff',
          borderWidth: 1,
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#64748b' } },
          y: { grid: { display: false }, ticks: { color: '#94a3b8' } }
        },
        plugins: { legend: { display: false } }
      }
    });
  }

  updateGeoChart(geoData) {
    if (!this.geoChart || !geoData) return;
    this.geoChart.data.labels = Object.keys(geoData);
    this.geoChart.data.datasets[0].data = Object.values(geoData);
    this.geoChart.update('none');
  }
}

export const chartManager = new ChartManager();
