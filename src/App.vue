<template>
  <div class="common-layout">
    <el-container>
      <el-card style="width: 100%; height: 95%">
        <template #header>
          <div  style="text-align: center;font-weight: bold">学习通AI自动考试程序</div></template>
        <div style="display: flex; align-content:flex-start">
          <div style="flex:3;">
            <div>学习通账号：<el-input v-model="username" style="width: 50%;margin-left: 10%" placeholder="请输入账号" /></div>
            <div style="margin-top: 10px">学习通密码：<el-input type="password" v-model="password" style="width: 50%;margin-left: 10%" placeholder="请输入密码" show-password /></div>
            <div style="margin-top: 10px">考试的链接：<el-input v-model="cxurl" style="width: 50%;margin-left: 10%" placeholder="进入考试后的第一题链接" /></div>
            <div style="margin-top: 10px">通义Token： <el-input v-model="tyapi" style="width: 50%;margin-left: 10%" placeholder="通义千问API TOKEN" /><a @click="startie('https://bailian.console.aliyun.com/?apiKey=1#/api-key')" style="margin-left: 10px" href="">申请API</a></div>
          </div>
          <div style="flex: 1; color: #666; font-size: 12px;">
            <div style="font-weight: bold; margin-bottom: 10px;">免责声明：</div>
            <div style="line-height: 1.5;">
              <p>本程序仅供学习和测试使用，请在下载24小时内删除，切勿用于考试舞弊等行为，所有使用本程序导致的后果皆由使用者自行承担，本项目不得用于违法违规用途，使用本程序即代表您同意此免责声明</p>
            </div>
          </div>
        </div>
        <template #footer>
          <div style="text-align: center">
            <el-button type="primary" @click="runCmd">开始考试</el-button>
            <div style="text-align: left">日志输出：</div>
            <pre id="output" style="text-align: left; margin-top: 10px; background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: calc(100vh - 430px); overflow-y: auto;"></pre>
            <div><a href="" @click="startie('https://github.com/myxuebi/chaoxingStudy-exam')">Github:myxuebi/chaoxingStudy-exam</a></div>
          </div>
        </template>
      </el-card>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const username = ref('');
const password = ref('');
const cxurl = ref('');
const tyapi = ref('');

const runCmd = () => {
  const command = `cmd /c py\\main.exe --username "${username.value}" --password "${password.value}" --url "${cxurl.value}" --api "${tyapi.value}"`;
  // const command = "ping 127.0.0.1 -n 5";
  window.electronAPI.send('run-cmd', command);
};

onMounted(() => {
  const output = document.getElementById('output');
  window.electronAPI.on('cmd-output', (event, data) => {
    output.textContent += data;
    output.scrollTop = output.scrollHeight;
  });
});

function startie(url){
  window.electronAPI.send('start-ie',url)
}
</script>

<style>
a, a:visited, a:link, a:hover{
  color:blue;
}
</style>
