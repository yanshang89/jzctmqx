// pages/config/config.js - 配置页面逻辑
const api = require('../../utils/api.js');
const app = getApp();

Page({
  data: {
    city: '',
    keyword: '',
    maxPage: '5',
    delay: '0.8',
    onlyTel: false,
    filterHotline: false,
    downloadImg: false,
    useProxy: false,
    proxyAddr: '',
    exportType: 'excel'
  },

  onLoad() {
    this.loadConfig();
  },

  // 加载配置
  async loadConfig() {
    try {
      const cfg = await api.getConfig();
      this.setData({
        city: cfg.city || '',
        keyword: cfg.keyword || '',
        maxPage: cfg.max_page || '5',
        delay: cfg.delay || '0.8',
        onlyTel: cfg.only_tel || false,
        filterHotline: cfg.filter_hotline || false,
        downloadImg: cfg.download_img || false,
        useProxy: cfg.use_proxy || false,
        proxyAddr: cfg.proxy_addr || '',
        exportType: cfg.export_type || 'excel'
      });
    } catch (e) {
      console.error('加载配置失败', e);
    }
  },

  // 输入框事件
  onCityInput(e) { this.setData({ city: e.detail.value }); },
  onKeywordInput(e) { this.setData({ keyword: e.detail.value }); },
  onPageInput(e) { this.setData({ maxPage: e.detail.value }); },
  onDelayInput(e) { this.setData({ delay: e.detail.value }); },
  onProxyInput(e) { this.setData({ proxyAddr: e.detail.value }); },

  // 复选框事件
  onOnlyTelChange(e) { this.setData({ onlyTel: e.detail.value }); },
  onFilterHotlineChange(e) { this.setData({ filterHotline: e.detail.value }); },
  onDownloadImgChange(e) { this.setData({ downloadImg: e.detail.value }); },
  onUseProxyChange(e) { this.setData({ useProxy: e.detail.value }); },

  // 设置导出格式
  setExportType(e) {
    this.setData({ exportType: e.currentTarget.dataset.type });
  },

  // 跳转到关键词搜索页
  goKeywordSearch() {
    wx.navigateTo({
      url: '/pages/keyword/keyword'
    });
  },

  // 保存配置
  async saveConfig() {
    const cfg = {
      city: this.data.city,
      keyword: this.data.keyword,
      max_page: this.data.maxPage,
      delay: this.data.delay,
      only_tel: this.data.onlyTel,
      filter_hotline: this.data.filterHotline,
      download_img: this.data.downloadImg,
      use_proxy: this.data.useProxy,
      proxy_addr: this.data.proxyAddr,
      export_type: this.data.exportType
    };
    try {
      const data = await api.saveConfig(cfg);
      // 缓存到本地
      wx.setStorageSync('user_config', cfg);
      app.globalData.config = cfg;
      wx.showToast({ title: data.msg, icon: 'success' });
    } catch (e) {
      wx.showToast({ title: '保存失败', icon: 'none' });
    }
  }
});
