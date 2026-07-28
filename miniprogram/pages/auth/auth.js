// pages/auth/auth.js - 授权页面逻辑
const api = require('../../utils/api.js');
const app = getApp();

Page({
  data: {
    machineCode: '',
    authCode: '',
    authStatus: '',     // 'success' / 'error' / ''
    authMsg: ''
  },

  onLoad() {
    this.loadMachineCode();
    this.checkAuth();
  },

  // 获取机器码
  async loadMachineCode() {
    try {
      const data = await api.getMachineCode();
      this.setData({ machineCode: data.machine_code });
    } catch (e) {
      console.error('获取机器码失败', e);
    }
  },

  // 输入激活码
  onAuthInput(e) {
    this.setData({ authCode: e.detail.value });
  },

  // 复制机器码
  copyMachineCode() {
    wx.setClipboardData({
      data: this.data.machineCode,
      success: () => {
        wx.showToast({ title: '机器码已复制', icon: 'success' });
      }
    });
  },

  // 校验授权
  async verifyAuth() {
    const code = this.data.authCode.trim();
    if (!code) {
      wx.showToast({ title: '请输入激活码', icon: 'none' });
      return;
    }
    try {
      const data = await api.verifyAuth(code);
      if (data.ok) {
        this.setData({
          authStatus: 'success',
          authMsg: '授权已通过'
        });
        app.globalData.authPassed = true;
        wx.showToast({ title: data.msg, icon: 'success' });
      } else {
        this.setData({
          authStatus: 'error',
          authMsg: '授权失败'
        });
        wx.showToast({ title: data.msg, icon: 'none' });
      }
    } catch (e) {
      wx.showToast({ title: '网络错误', icon: 'none' });
    }
  },

  // 检查授权状态
  async checkAuth() {
    try {
      const data = await api.checkAuth();
      if (data.ok) {
        this.setData({
          authStatus: 'success',
          authMsg: '授权已通过'
        });
        app.globalData.authPassed = true;
      }
    } catch (e) {}
  }
});
