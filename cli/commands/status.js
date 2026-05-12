/**
 * 查看状态命令
 *
 * 查询仿写任务的当前状态和进度。
 * 支持单次查询、持续监控、列出所有任务。
 */

const { Command } = require('commander');
const inquirer = require('inquirer');
const ora = require('ora');
const api = require('../utils/api');
const display = require('../utils/display');

const command = new Command('status');

command
  .description('查看仿写任务状态')
  .argument('[task_id]', '任务ID（不提供则列出所有任务）')
  .option('-w, --watch', '持续监控状态')
  .option('-i, --interval <seconds>', '刷新间隔（秒）', '5')
  .option('-l, --list', '列出所有任务')
  .option('--copyright', '查看版权检测报告')
  .option('--originality', '查看原创性报告')
  .action(async (taskId, options) => {
    try {
      // 列出所有任务模式
      if (options.list || !taskId) {
        const spinner = ora('获取任务列表...').start();
        try {
          const tasks = await api.listTasks();
          spinner.succeed('查询成功');
          display.title('任务列表');
          display.taskList(tasks);

          // 如果有任务，提供交互选择
          if (tasks && tasks.length > 0 && !options.list) {
            const choices = tasks.map((t) => ({
              name: `${t.task_id}  ${t.novel_name || '(未命名)'}  [${t.status}]`,
              value: t.task_id,
            }));

            const { selectedTaskId } = await inquirer.prompt([
              {
                type: 'list',
                name: 'selectedTaskId',
                message: '选择要查看的任务:',
                choices,
              },
            ]);

            taskId = selectedTaskId;
            // 继续执行下面的状态查询
          } else {
            return;
          }
        } catch (err) {
          spinner.fail('查询失败');
          display.error(err.message);
          process.exit(1);
        }
      }

      // 版权检测报告模式
      if (options.copyright) {
        const spinner = ora('获取版权检测报告...').start();
        try {
          const report = await api.getCopyrightReport(taskId);
          spinner.succeed('查询成功');
          display.title(`版权检测报告 - ${taskId}`);
          display.copyrightReport(report);
        } catch (err) {
          spinner.fail('查询失败');
          display.error(err.message);
          process.exit(1);
        }
        return;
      }

      // 原创性报告模式
      if (options.originality) {
        const spinner = ora('获取原创性报告...').start();
        try {
          const report = await api.getOriginalityReport(taskId);
          spinner.succeed('查询成功');
          display.title(`原创性报告 - ${taskId}`);
          display.originalityReport(report);
        } catch (err) {
          spinner.fail('查询失败');
          display.error(err.message);
          process.exit(1);
        }
        return;
      }

      // 持续监控模式
      if (options.watch) {
        display.title(`任务监控: ${taskId}`);
        const interval = parseInt(options.interval, 10) * 1000;

        const checkStatus = async () => {
          try {
            const status = await api.getTaskStatus(taskId);
            display.taskStatus(status);

            if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
              if (status.status === 'completed') {
                display.success('任务已完成!');
                display.info(`总字数: ${(status.total_words || 0).toLocaleString()} 字`);
                display.info(`总成本: ${(status.actual_cost || 0).toFixed(4)} 元`);
                display.info('使用 "novel-rewriter export <task_id>" 导出小说');
              } else if (status.status === 'failed') {
                display.error(`任务失败: ${status.error_message}`);
              } else {
                display.warning('任务已取消');
              }
              return true; // 停止监控
            }
            return false; // 继续监控
          } catch (err) {
            display.error(`查询失败: ${err.message}`);
            return true; // 出错停止
          }
        };

        // eslint-disable-next-line no-constant-condition
        while (true) {
          const shouldStop = await checkStatus();
          if (shouldStop) break;
          await new Promise(resolve => setTimeout(resolve, interval));
        }
      } else {
        // 单次查询模式
        const spinner = ora('查询任务状态...').start();
        try {
          const status = await api.getTaskStatus(taskId);
          spinner.succeed('查询成功');
          display.title(`任务状态 - ${taskId}`);
          display.taskStatus(status);

          // 如果任务进行中，提示可用操作
          if (status.status === 'generating' || status.status === 'building_world') {
            display.info('提示: 使用 --watch 选项持续监控进度');
          }
          if (status.status === 'paused') {
            display.info('提示: 使用 "novel-rewriter resume <task_id>" 恢复任务');
          }
          if (status.status === 'completed') {
            display.info('提示: 使用 "novel-rewriter export <task_id>" 导出小说');
            display.info('提示: 使用 --copyright 查看版权检测报告');
            display.info('提示: 使用 --originality 查看原创性报告');
          }
        } catch (err) {
          spinner.fail('查询失败');
          display.error(err.message);
          process.exit(1);
        }
      }

    } catch (err) {
      display.error(err.message);
      process.exit(1);
    }
  });

module.exports = command;
