// pages/keyword/keyword.js - 关键词搜索页面逻辑
const api = require('../../utils/api.js');

Page({
  data: {
    searchKey: '',
    keywords: [],
    selectedKeyword: '',
    currentKeyword: ''  // 当前配置中的关键词
  },

  onLoad() {
    // 从配置页传过来的当前关键词
    const pages = getCurrentPages();
    const prevPage = pages[pages.length - 2];
    if (prevPage) {
      this.setData({ currentKeyword: prevPage.data.keyword });
    }
    this.searchKeyword();
  },

  // 搜索框输入
  onSearchInput(e) {
    this.setData({ searchKey: e.detail.value });
  },

  // 执行搜索
  async searchKeyword() {
    try {
      const data = await api.getKeywords(this.data.searchKey);
      this.setData({ keywords: data || [] });
    } catch (e) {
      console.error('搜索关键词失败', e);
    }
  },

  // 选择关键词
  selectKeyword(e) {
    const kw = e.currentTarget.dataset.kw;
    this.setData({ selectedKeyword: kw });
  },

  // 追加到现有关键词
  appendKeyword() {
    if (!this.data.selectedKeyword) {
      wx.showToast({ title: '请先选择关键词', icon: 'none' });
      return;
    }
    const pages = getCurrentPages();
    const prevPage = pages[pages.length - 2];
    if (prevPage) {
      let current = prevPage.data.keyword.trim();
      if (current) {
        const arr = current.split(',');
        if (!arr.includes(this.data.selectedKeyword)) {
          current = current + ',' + this.data.selectedKeyword;
        }
      } else {
        current = this.data.selectedKeyword;
      }
      prevPage.setData({ keyword: current });
    }
    wx.showToast({ title: '已追加', icon: 'success' });
    setTimeout(() => wx.navigateBack(), 800);
  },

  // 替换现有关键词
  replaceKeyword() {
    if (!this.data.selectedKeyword) {
      wx.showToast({ title: '请先选择关键词', icon: 'none' });
      return;
    }
    const pages = getCurrentPages();
    const prevPage = pages[pages.length - 2];
    if (prevPage) {
      prevPage.setData({ keyword: this.data.selectedKeyword });
    }
    wx.showToast({ title: '已替换', icon: 'success' });
    setTimeout(() => wx.navigateBack(), 800);
  }
});
