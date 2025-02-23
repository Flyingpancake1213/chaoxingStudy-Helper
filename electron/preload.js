const { contextBridge, ipcRenderer } = require('electron');

// 安全地暴露 ipcRenderer 方法
contextBridge.exposeInMainWorld('electronAPI', {
    send: (channel, data) => ipcRenderer.send(channel, data),
    on: (channel, callback) => ipcRenderer.on(channel, callback),
});