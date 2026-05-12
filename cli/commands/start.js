/**
 * 开始仿写命令
 *
 * 交互式引导用户配置仿写参数并启动任务。
 * 支持命令行参数直接传入或交互式填写。
 */

const { Command } = require('commander');
const inquirer = require('inquirer');
const ora = require('ora');
const api = require('../utils/api');
const display = require('../utils/display');

const command = new Command('start');

command
  .description('开始仿写小说')
  .option('-n, --name <name>', '小说名称')
  .option('-g, --genre <genre>', '小说类型')
  .option('-p, --protagonist <name>', '主角名称')
  .option('-c, --chapters <number>', '总章数', '300')
  .option('-w, --words <number>', '每章字数', '3000')
  .option('-s, --source <path>', '源小说路径')
  .option('-d, --description <desc>', '小说描述')
  .option('--no-deai', '禁用去AI化处理')
  .option('--no-copyright', '禁用版权检测')
  .option('--no-quality', '禁用质量检查')
  .action(async (options) => {
    try {
      display.title('仿写百万字小说');

      // 检查后端服务
      const spinner = ora('检查后端服务...').start();
      try {
        await api.healthCheck();
        spinner.succeed('后端服务已连接');
      } catch (err) {
        spinner.fail('无法连接到后端服务');
        display.error('请确保后端服务已启动: python -m uvicorn backend.main:app --reload');
        process.exit(1);
      }

      // 获取可用类型
      let genres = [];
      try {
        genres = await api.getGenres();
      } catch (err) {
        genres = ['玄幻', '仙侠', '都市', '科幻', '历史', '游戏', '悬疑', '言情'];
      }

      // 交互式配置
      const answers = await inquirer.prompt([
        {
          type: 'input',
          name: 'novel_name',
          message: '小说名称:',
          default: options.name || '',
          validate: (input) => input.trim() ? true : '请输入小说名称',
        },
        {
          type: 'list',
          name: 'genre',
          message: '小说类型:',
          choices: genres,
          default: options.genre || '玄幻',
        },
        {
          type: 'input',
          name: 'protagonist_name',
          message: '主角名称:',
          default: options.protagonist || '',
          validate: (input) => input.trim() ? true : '请输入主角名称',
        },
        {
          type: 'number',
          name: 'total_chapters',
          message: '总章数:',
          default: parseInt(options.chapters, 10) || 300,
          validate: (input) => input > 0 ? true : '章数必须大于0',
        },
        {
          type: 'number',
          name: 'chapter_words',
          message: '每章目标字数:',
          default: parseInt(options.words, 10) || 3000,
          validate: (input) => input > 0 ? true : '字数必须大于0',
        },
        {
          type: 'input',
          name: 'source_novel_path',
          message: '源小说路径（留空则从零开始创作）:',
          default: options.source || '',
        },
        {
          type: 'input',
          name: 'novel_description',
          message: '小说简介:',
          default: options.description || '',
        },
      ]);

      // 确认信息
      display.separator();
      display.keyValue('小说名称', answers.novel_name);
      display.keyValue('类型', answers.genre);
      display.keyValue('主角', answers.protagonist_name);
      display.keyValue('总章数', String(answers.total_chapters));
      display.keyValue('每章字数', String(answers.chapter_words));
      display.keyValue('总目标字数', String(answers.total_chapters * answers.chapter_words));
      display.keyValue('源小说', answers.source_novel_path || '无（从零创作）');
      display.keyValue('去AI化', options.deai ? '关闭' : '开启');
      display.keyValue('版权检测', options.copyright ? '关闭' : '开启');
      display.keyValue('质量检查', options.quality ? '关闭' : '开启');
      display.separator();

      const confirm = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'proceed',
          message: '确认开始仿写？',
          default: true,
        },
      ]);

      if (!confirm.proceed) {
        display.warning('已取消');
        process.exit(0);
      }

      // 构建请求参数
      const params = {
        novel_name: answers.novel_name,
        genre: answers.genre,
        protagonist_name: answers.protagonist_name,
        total_chapters: answers.total_chapters,
        chapter_words: answers.chapter_words,
        source_novel_path: answers.source_novel_path,
        novel_description: answers.novel_description,
        enable_deai: !options.deai,
        enable_copyright_check: !options.copyright,
        enable_quality_check: !options.quality,
      };

      // 启动任务
      const startSpinner = ora('启动仿写任务...').start();
      const result = await api.startRewrite(params);
      startSpinner.succeed(`任务已创建: ${result.task_id}`);

      display.success(`任务ID: ${result.task_id}`);
      display.info('使用 "novel-rewriter status <task_id>" 查看进度');
      display.info('使用 "novel-rewriter status <task_id> --watch" 持续监控');

    } catch (err) {
      display.error(err.message);
      process.exit(1);
    }
  });

module.exports = command;
