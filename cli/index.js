#!/usr/bin/env node

/**
 * 仿写百万字小说软件 - CLI入口
 *
 * 使用方法:
 *   novel-rewriter start    - 开始仿写
 *   novel-rewriter status   - 查看状态
 *   novel-rewriter export   - 导出小说
 *   novel-rewriter pause    - 暂停任务
 *   novel-rewriter resume   - 恢复任务
 */

const { Command } = require('commander');
const startCommand = require('./commands/start');
const statusCommand = require('./commands/status');
const exportCommand = require('./commands/export');
const api = require('./utils/api');
const display = require('./utils/display');

const program = new Command();

program
  .name('novel-rewriter')
  .description('仿写百万字小说软件 - 基于AI的长篇小说仿写工具')
  .version('0.1.0');

// 注册子命令
program.addCommand(startCommand);
program.addCommand(statusCommand);
program.addCommand(exportCommand);

// 暂停任务命令
program
  .command('pause <task_id>')
  .description('暂停正在运行的仿写任务')
  .action(async (taskId) => {
    try {
      const spinner = ora('暂停任务...').start();
      try {
        await api.pauseTask(taskId);
        spinner.succeed(`任务 ${taskId} 已暂停`);
        display.info('使用 "novel-rewriter resume <task_id>" 恢复任务');
      } catch (err) {
        spinner.fail('暂停失败');
        display.error(err.message);
        process.exit(1);
      }
    } catch (err) {
      display.error(err.message);
      process.exit(1);
    }
  });

// 恢复任务命令
program
  .command('resume <task_id>')
  .description('恢复已暂停的仿写任务（断点续传）')
  .action(async (taskId) => {
    try {
      const spinner = ora('恢复任务...').start();
      try {
        const result = await api.resumeTask(taskId);
        spinner.succeed(`任务 ${taskId} 已恢复`);
        display.info('使用 "novel-rewriter status <task_id> --watch" 监控进度');
      } catch (err) {
        spinner.fail('恢复失败');
        display.error(err.message);
        process.exit(1);
      }
    } catch (err) {
      display.error(err.message);
      process.exit(1);
    }
  });

// 默认显示帮助
program.action(() => {
  program.help();
});

program.parse(process.argv);
