// pages/collect/collect.js - 采集页面逻辑
const api = require('../../utils/api.js');

Page({
  data: {
    stat: {
      current: 0,
      history: 0,
      skip_repeat: 0,
      no_tel: 0
    },
    running: false,
    dataList: [],
    logs: [],
    startBtnDisabled: false
  },

  refreshTimer: null,

  onLoad() {
    // 进入页面就开始刷新
  },

  onShow() {
    this.startRefresh();
  },

  onHide() {
    this.stopRefresh();
  },

  onUnload() {
    this.stopRefresh();
  },

  // 开始采集
  async startCollect() {
    try {
      const data = await api.startCollect();
      if (data.ok) {
        wx.showToast({ title: data.msg, icon: 'success' });
        this.setData({ startBtnDisabled: true });
        this.startRefresh();
      } else {
        wx.showToast({ title: data.msg, icon: 'none' });
      }
    } catch (e) {
      wx.showToast({ title: '网络错误', icon: 'none' });
    }
  },

  // 停止采集
  async stopCollect() {
    try {
      await api.stopCollect();
      wx.showToast({ title: '已停止采集', icon: 'success' });
      this.setData({ startBtnDisabled: false });
    } catch (e) {}
  },

  // 清空数据
  async clearData() {
    wx.showModal({
      title: '提示',
      content: '确认清空采集数据？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.clearData();
            wx.showToast({ title: '数据已清空', icon: 'success' });
            this.refreshData();
          } catch (e) {}
        }
      }
    });
  },

  // 导出数据
  async exportData() {
    if (this.data.dataList.length === 0) {
      wx.showToast({ title: '暂无数据可导出', icon: 'none' });
      return;
    }
    try {
      await api.exportData();
      wx.showToast({ title: '导出成功', icon: 'success' });
    } catch (e) {
      wx.showToast({ title: '导出失败', icon: 'none' });
    }
  },

  // 刷新数据
  async refreshData() {
    try {
      const data = await api.getData();
      this.setData({
        stat: data.stat,
        dataList: data.data || [],
        logs: data.logs || [],
        running: data.running,
        startBtnDisabled: data.running
      });
    } catch (e) {}
  },

  // 定时刷新
  startRefresh() {
    this.refreshData();
    this.refreshTimer = setInterval(() => {
      this.refreshData();
    }, 1500);
  },

  stopRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  },

  // 拨打电话
  callPhone(e) {
    const phone = e.currentTarget.dataset.phone;
    if (!phone) {
      wx.showToast({ title: '无电话号码', icon: 'none' });
      return;
    }
    wx.makePhoneCall({
      phoneNumber: phone.replace(/-/g, ''),
      fail: () => {}
    });
  },

  // 复制电话
  copyPhone(e) {
    const phone = e.currentTarget.dataset.phone;
    if (!phone) return;
    wx.setClipboardData({
      data: phone,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
      }
    });
  }
});
