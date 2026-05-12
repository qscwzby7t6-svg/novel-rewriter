/**
 * 终端显示工具
 *
 * 提供终端美化输出功能，包括标题、状态、进度条、表格等。
 */

const chalk = require('chalk');

/**
 * 显示标题
 * @param {string} text - 标题文本
 */
function title(text) {
  console.log('');
  console.log(chalk.bold.cyan('========================================'));
  console.log(chalk.bold.cyan(`  ${text}`));
  console.log(chalk.bold.cyan('========================================'));
  console.log('');
}

/**
 * 显示成功信息
 * @param {string} text - 信息文本
 */
function success(text) {
  console.log(chalk.green(`  [成功] ${text}`));
}

/**
 * 显示错误信息
 * @param {string} text - 信息文本
 */
function error(text) {
  console.log(chalk.red(`  [错误] ${text}`));
}

/**
 * 显示警告信息
 * @param {string} text - 信息文本
 */
function warning(text) {
  console.log(chalk.yellow(`  [警告] ${text}`));
}

/**
 * 显示信息
 * @param {string} text - 信息文本
 */
function info(text) {
  console.log(chalk.blue(`  [信息] ${text}`));
}

/**
 * 显示进度条
 * @param {number} current - 当前进度
 * @param {number} total - 总数
 * @param {string} prefix - 前缀文本
 */
function progressBar(current, total, prefix = '进度') {
  const percent = Math.round((current / total) * 100);
  const filled = Math.round((current / total) * 30);
  const empty = 30 - filled;
  const bar = chalk.green('█'.repeat(filled)) + chalk.gray('░'.repeat(empty));
  process.stdout.write(`\r  ${prefix}: [${bar}] ${percent}% (${current}/${total})`);
  if (current === total) {
    console.log('');
  }
}

/**
 * 显示分隔线
 */
function separator() {
  console.log(chalk.gray('  ─────────────────────────────────────'));
}

/**
 * 显示键值对
 * @param {string} key - 键名
 * @param {string} value - 值
 */
function keyValue(key, value) {
  console.log(`  ${chalk.gray(key)}: ${chalk.white(value)}`);
}

/**
 * 状态文本着色
 * @param {string} status - 状态值
 * @returns {string} 着色后的状态文本
 */
function colorStatus(status) {
  const statusColors = {
    pending: chalk.gray,
    parsing: chalk.cyan,
    building_world: chalk.cyan,
    generating: chalk.yellow,
    checking_quality: chalk.yellow,
    optimizing: chalk.yellow,
    paused: chalk.hex('#FFA500'),
    completed: chalk.green,
    failed: chalk.red,
    cancelled: chalk.red,
  };
  const colorFn = statusColors[status] || chalk.white;
  return colorFn(status);
}

/**
 * 版权风险着色
 * @param {string} risk - 风险等级
 * @returns {string} 着色后的风险文本
 */
function colorRisk(risk) {
  const riskColors = {
    safe: chalk.green,
    low: chalk.hex('#87CEEB'),
    medium: chalk.yellow,
    high: chalk.red,
  };
  const colorFn = riskColors[risk] || chalk.white;
  return colorFn(risk);
}

/**
 * 显示任务状态摘要
 * @param {Object} status - 任务状态对象
 */
function taskStatus(status) {
  separator();
  keyValue('任务ID', status.task_id || '-');
  keyValue('小说名称', status.novel_name || '-');
  keyValue('状态', colorStatus(status.status || 'unknown'));
  keyValue('进度', `${(status.progress || 0).toFixed(1)}%`);
  keyValue('当前章节', `${status.current_chapter || 0} / ${status.total_chapters || 0}`);
  keyValue('已完成章节', String(status.completed_chapters || 0));
  keyValue('总字数', `${(status.total_words || 0).toLocaleString()} 字`);
  keyValue('预估成本', `${(status.estimated_cost || 0).toFixed(4)} 元`);
  keyValue('实际成本', `${(status.actual_cost || 0).toFixed(4)} 元`);

  if (status.start_time) {
    keyValue('开始时间', status.start_time);
  }
  if (status.end_time) {
    keyValue('结束时间', status.end_time);
  }
  if (status.error_message) {
    keyValue('错误信息', chalk.red(status.error_message));
  }

  separator();
}

/**
 * 显示任务列表
 * @param {Object[]} tasks - 任务列表
 */
function taskList(tasks) {
  if (!tasks || tasks.length === 0) {
    info('暂无任务记录');
    return;
  }

  console.log('');
  // 表头
  const header = '  ' +
    chalk.gray('ID'.padEnd(12)) +
    chalk.gray('名称'.padEnd(20)) +
    chalk.gray('状态'.padEnd(16)) +
    chalk.gray('进度'.padEnd(10)) +
    chalk.gray('章节'.padEnd(14)) +
    chalk.gray('成本');
  console.log(header);
  separator();

  for (const task of tasks) {
    const id = (task.task_id || '-').padEnd(12);
    const name = (task.novel_name || '-').substring(0, 18).padEnd(20);
    const status = colorStatus(task.status || 'unknown').padEnd(16);
    const progress = `${(task.progress || 0).toFixed(1)}%`.padEnd(10);
    const chapters = `${task.current_chapter || 0}/${task.total_chapters || 0}`.padEnd(14);
    const cost = `${(task.actual_cost || 0).toFixed(4)}元`;

    console.log(`  ${id}${name}${status}${progress}${chapters}${cost}`);
  }
  console.log('');
}

/**
 * 显示版权检测报告
 * @param {Object} report - 版权检测报告
 */
function copyrightReport(report) {
  separator();
  keyValue('版权相似度', `${((report.copyright_similarity || 0) * 100).toFixed(2)}%`);
  keyValue('风险等级', colorRisk(report.risk_level || 'safe'));

  if (report.ngram) {
    console.log('');
    info('N-gram 检测:');
    keyValue('  相似度', `${(report.ngram.similarity * 100).toFixed(2)}%`);
    keyValue('  匹配片段', `${report.ngram.matching_ngrams}/${report.ngram.total_ngrams}`);
    keyValue('  风险', colorRisk(report.ngram.risk_level));
  }

  if (report.sentence) {
    console.log('');
    info('句子级检测:');
    keyValue('  相似度', `${(report.sentence.similarity * 100).toFixed(2)}%`);
    keyValue('  完全相同句子', String(report.sentence.identical_sentences));
    keyValue('  相似句子', String(report.sentence.similar_sentences));
    keyValue('  风险', colorRisk(report.sentence.risk_level));
  }

  if (report.paragraph) {
    console.log('');
    info('段落级检测:');
    keyValue('  最高相似度', `${(report.paragraph.similarity * 100).toFixed(2)}%`);
    keyValue('  平均相似度', `${(report.paragraph.avg_similarity * 100).toFixed(2)}%`);
    keyValue('  高风险段落', String(report.paragraph.high_risk_paragraphs));
    keyValue('  风险', colorRisk(report.paragraph.risk_level));
  }

  if (report.issues && report.issues.length > 0) {
    console.log('');
    warning(`发现 ${report.issues.length} 个问题:`);
    for (const issue of report.issues) {
      const icon = issue.severity === 'error' ? chalk.red('x') : chalk.yellow('!');
      console.log(`    ${icon} [${issue.type}] ${issue.description}`);
      if (issue.suggestion) {
        console.log(`      ${chalk.gray('建议:')} ${issue.suggestion}`);
      }
    }
  }

  separator();
}

/**
 * 显示原创性报告
 * @param {Object} report - 原创性报告
 */
function originalityReport(report) {
  separator();
  keyValue('综合原创性', `${((report.overall_originality || 0) * 100).toFixed(2)}%`);

  if (report.dimensions) {
    console.log('');
    info('各维度评分:');
    const dimLabels = {
      world_setting: '世界观',
      characters: '角色',
      power_system: '力量体系',
      plot: '情节',
    };

    for (const [key, value] of Object.entries(report.dimensions)) {
      const label = dimLabels[key] || key;
      const score = (value.score || 0) * 100;
      const colorFn = score >= 70 ? chalk.green : score >= 50 ? chalk.yellow : chalk.red;
      keyValue(`  ${label}`, colorFn(`${score.toFixed(1)}%`));
      if (value.reason) {
        console.log(`    ${chalk.gray(value.reason)}`);
      }
    }
  }

  if (report.suggestions && report.suggestions.length > 0) {
    console.log('');
    info('建议:');
    for (const suggestion of report.suggestions) {
      console.log(`  - ${suggestion}`);
    }
  }

  separator();
}

module.exports = {
  title,
  success,
  error,
  warning,
  info,
  progressBar,
  separator,
  keyValue,
  colorStatus,
  colorRisk,
  taskStatus,
  taskList,
  copyrightReport,
  originalityReport,
};
