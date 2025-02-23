const { app, BrowserWindow, Menu , ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const iconv = require('iconv-lite');

function createWindow() {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
        title: "超星AI自动答题",
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false
        },
    });

    if (process.env.NODE_ENV === 'development') {
        win.loadURL('http://localhost:8080');
        // win.webContents.openDevTools();
    } else {
        win.loadFile(path.join(__dirname, '../dist-web/index.html'));
    }
    // win.loadFile(path.join(__dirname, '../dist-web/index.html'));
    // win.webContents.openDevTools();
}

app.whenReady().then(() =>{
    Menu.setApplicationMenu(null);
    createWindow();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

ipcMain.on('run-cmd', (event, command) => {
    const cmdProcess = spawn(command, { shell: true });

    // 实时输出日志（将 GBK 转换为 UTF-8）
    cmdProcess.stdout.on('data', (data) => {
        const utf8Data = iconv.decode(data, 'gbk'); // 转换编码
        event.reply('cmd-output', utf8Data);
    });

    cmdProcess.stderr.on('data', (data) => {
        const utf8Data = iconv.decode(data, 'gbk'); // 转换编码
        event.reply('cmd-output', utf8Data);
    });

    cmdProcess.on('close', (code) => {
        event.reply('cmd-output', `命令执行完毕，退出码：${code}`);
    });
});