/**
 * 导出命令
 *
 * 将生成的小说导出为指定格式（txt/json/docx）。
 * 支持交互式选择和命令行参数两种方式。
 */

const { Command } = require('commander');
const inquirer = require('inquirer');
const ora = require('ora');
const path = require('path');
const api = require('../utils/api');
const display = require('../utils/display');

const command = new Command('export');

command
  .description('导出仿写完成的小说')
  .argument('[task_id]', '任务ID')
  .option('-f, --format <format>', '输出格式 (txt/json/docx)', 'txt')
  .option('-o, --output <path>', '输出路径')
  .option('-a, --all', '导出所有已完成章节（默认）')
  .option('--chapters <range>', '指定章节范围，如 "1-10,15,20-30"')
  .action(async (taskId, options) => {
    try {
      display.title('导出小说');

      // 如果没有提供task_id，交互式输入
      if (!taskId) {
        // 尝试列出任务供选择
        let tasks = [];
        try {
          tasks = await api.listTasks();
        } catch (err) {
          // 忽略，回退到手动输入
        }

        if (tasks && tasks.length > 0) {
          const choices = tasks.map((t) => ({
            name: `${t.task_id}  ${t.novel_name || '(未命名)'}  [${t.status}]  ${(t.total_words || 0).toLocaleString()}字`,
            value: t.task_id,
          }));

          choices.push({ name: '手动输入任务ID', value: '__manual__' });

          const { selectedTaskId } = await inquirer.prompt([
            {
              type: 'list',
              name: 'selectedTaskId',
              message: '选择要导出的任务:',
              choices,
            },
          ]);

          if (selectedTaskId === '__manual__') {
            const manualAnswer = await inquirer.prompt([
              {
                type: 'input',
                name: 'task_id',
                message: '任务ID:',
                validate: (input) => input.trim() ? true : '请输入任务ID',
              },
            ]);
            taskId = manualAnswer.task_id;
          } else {
            taskId = selectedTaskId;
          }
        } else {
          const answers = await inquirer.prompt([
            {
              type: 'input',
              name: 'task_id',
              message: '任务ID:',
              validate: (input) => input.trim() ? true : '请输入任务ID',
            },
          ]);
          taskId = answers.task_id;
        }
      }

      // 查询任务状态
      const spinner = ora('查询任务状态...').start();
      let status;
      try {
        status = await api.getTaskStatus(taskId);
        spinner.succeed('任务状态查询成功');
      } catch (err) {
        spinner.fail('查询失败');
        display.error(err.message);
        process.exit(1);
      }

      display.taskStatus(status);

      if (status.status !== 'completed') {
        display.warning('任务尚未完成，导出的内容可能不完整');
        const confirm = await inquirer.prompt([
          {
            type: 'confirm',
            name: 'proceed',
            message: '是否仍然导出？',
            default: false,
          },
        ]);
        if (!confirm.proceed) {
          process.exit(0);
        }
      }

      // 选择导出格式
      const formatChoices = [
        { name: 'TXT (纯文本)', value: 'txt' },
        { name: 'JSON (结构化数据)', value: 'json' },
        { name: 'DOCX (Word文档)', value: 'docx' },
      ];

      const formatAnswer = await inquirer.prompt([
        {
          type: 'list',
          name: 'format',
          message: '导出格式:',
          choices: formatChoices,
          default: options.format || 'txt',
        },
      ]);

      // 输出路径
      const defaultOutput = options.output || path.join(
        'data', 'output',
        `novel_${taskId}.${formatAnswer.format}`
      );

      const outputAnswer = await inquirer.prompt([
        {
          type: 'input',
          name: 'output_path',
          message: '输出路径:',
          default: defaultOutput,
        },
      ]);

      // 执行导出
      const exportSpinner = ora('正在导出...').start();
      try {
        const result = await api.exportNovel(
          taskId,
          formatAnswer.format,
          outputAnswer.output_path,
        );
        exportSpinner.succeed('导出成功');

        display.success(`文件已保存: ${outputAnswer.output_path}`);

        if (result.file_size) {
          display.info(`文件大小: ${(result.file_size / 1024).toFixed(1)} KB`);
        }
        if (result.chapter_count) {
          display.info(`导出章节数: ${result.chapter_count}`);
        }
        if (result.total_words) {
          display.info(`总字数: ${result.total_words.toLocaleString()}`);
        }
      } catch (err) {
        exportSpinner.fail('导出失败');
        display.error(err.message);
        process.exit(1);
      }

    } catch (err) {
      display.error(err.message);
      process.exit(1);
    }
  });

module.exports = command;
