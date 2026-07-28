// utils/api.js - 封装后端API请求
// 所有对Flask后端的请求都通过这里统一处理

const app = getApp();

// 通用请求方法
function request(options) {
  return new Promise((resolve, reject) => {
    const url = app.globalData.baseUrl + options.url;
    wx.request({
      url: url,
      method: options.method || 'GET',
      data: options.data || {},
      header: Object.assign({
        'Content-Type': 'application/json'
      }, options.header || {}),
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(new Error('请求失败: ' + res.statusCode));
        }
      },
      fail: (err) => {
        reject(err);
      }
    });
  });
}

// 获取机器码
function getMachineCode() {
  return request({ url: '/api/machine_code' });
}

// 校验授权
function verifyAuth(authCode) {
  return request({
    url: '/api/verify_auth',
    method: 'POST',
    data: { auth_code: authCode }
  });
}

// 检查授权状态
function checkAuth() {
  return request({ url: '/api/check_auth' });
}

// 获取配置
function getConfig() {
  return request({ url: '/api/config' });
}

// 保存配置
function saveConfig(cfg) {
  return request({
    url: '/api/config',
    method: 'POST',
    data: cfg
  });
}

// 获取关键词列表
function getKeywords(q) {
  return request({ url: '/api/keywords?q=' + encodeURIComponent(q || '') });
}

// 开始采集
function startCollect() {
  return request({ url: '/api/start_collect', method: 'POST' });
}

// 停止采集
function stopCollect() {
  return request({ url: '/api/stop_collect' });
}

// 清空数据
function clearData() {
  return request({ url: '/api/clear_data' });
}

// 获取采集数据
function getData() {
  return request({ url: '/api/data' });
}

// 导出数据 - 小程序需用 downloadFile + openDocument
function exportData() {
  return new Promise((resolve, reject) => {
    const url = app.globalData.baseUrl + '/api/export';
    wx.showLoading({ title: '正在导出...' });
    wx.downloadFile({
      url: url,
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200) {
          // 用文档预览打开
          wx.openDocument({
            filePath: res.tempFilePath,
            showMenu: true,
            success: () => resolve(true),
            fail: (err) => reject(err)
          });
        } else {
          reject(new Error('导出失败'));
        }
      },
      fail: (err) => {
        wx.hideLoading();
        reject(err);
      }
    });
  });
}

module.exports = {
  request,
  getMachineCode,
  verifyAuth,
  checkAuth,
  getConfig,
  saveConfig,
  getKeywords,
  startCollect,
  stopCollect,
  clearData,
  getData,
  exportData
};
