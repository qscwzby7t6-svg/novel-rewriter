/**
 * API通信模块
 *
 * 封装与后端FastAPI服务的HTTP通信。
 * 支持健康检查、任务管理、状态查询、导出等功能。
 */

const axios = require('axios');

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000';

class ApiClient {
  constructor(baseUrl = DEFAULT_BASE_URL) {
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 响应拦截器：统一错误处理
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.code === 'ECONNABORTED') {
          throw new Error('请求超时，后端服务可能无响应');
        }
        if (error.code === 'ECONNREFUSED') {
          throw new Error('无法连接到后端服务，请确认服务已启动');
        }
        if (error.response) {
          const status = error.response.status;
          const data = error.response.data;
          const message = data?.detail || data?.message || `服务器错误 (${status})`;
          throw new Error(message);
        }
        throw new Error(`网络错误: ${error.message}`);
      }
    );
  }

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康状态
   */
  async healthCheck() {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`无法连接到后端服务: ${error.message}`);
    }
  }

  /**
   * 获取当前配置
   * @returns {Promise<Object>} 配置信息
   */
  async getConfig() {
    const response = await this.client.get('/api/config');
    return response.data;
  }

  /**
   * 获取支持的小说类型
   * @returns {Promise<string[]>} 类型列表
   */
  async getGenres() {
    const response = await this.client.get('/api/genres');
    return response.data.genres;
  }

  /**
   * 开始仿写任务
   * @param {Object} params - 仿写参数
   * @param {string} params.novel_name - 小说名称
   * @param {string} params.genre - 小说类型
   * @param {number} params.total_chapters - 总章数
   * @param {number} params.chapter_words - 每章字数
   * @param {string} params.source_novel_path - 源小说路径
   * @param {string} params.novel_description - 小说描述
   * @param {string} params.protagonist_name - 主角名称
   * @returns {Promise<Object>} 任务创建结果 { task_id, ... }
   */
  async startRewrite(params) {
    const response = await this.client.post('/api/rewrite/start', params);
    return response.data;
  }

  /**
   * 查询任务状态
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 任务状态信息
   */
  async getTaskStatus(taskId) {
    const response = await this.client.get(`/api/rewrite/${taskId}/status`);
    return response.data;
  }

  /**
   * 列出所有任务
   * @returns {Promise<Object[]>} 任务列表
   */
  async listTasks() {
    const response = await this.client.get('/api/rewrite/tasks');
    return response.data.tasks || [];
  }

  /**
   * 暂停任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 暂停结果
   */
  async pauseTask(taskId) {
    const response = await this.client.post(`/api/rewrite/${taskId}/pause`);
    return response.data;
  }

  /**
   * 恢复任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 恢复结果
   */
  async resumeTask(taskId) {
    const response = await this.client.post(`/api/rewrite/${taskId}/resume`);
    return response.data;
  }

  /**
   * 取消任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 取消结果
   */
  async cancelTask(taskId) {
    const response = await this.client.post(`/api/rewrite/${taskId}/cancel`);
    return response.data;
  }

  /**
   * 导出小说
   * @param {string} taskId - 任务ID
   * @param {string} format - 输出格式 (txt/json/docx)
   * @param {string} outputPath - 输出路径
   * @returns {Promise<Object>} 导出结果 { file_path, ... }
   */
  async exportNovel(taskId, format = 'txt', outputPath = '') {
    const response = await this.client.post('/api/export', {
      task_id: taskId,
      format,
      output_path: outputPath,
    });
    return response.data;
  }

  /**
   * 获取版权检测报告
   * @param {string} taskId - 任务ID
   * @param {number} chapterNumber - 章节号（可选）
   * @returns {Promise<Object>} 版权检测报告
   */
  async getCopyrightReport(taskId, chapterNumber = null) {
    const params = {};
    if (chapterNumber !== null) {
      params.chapter = chapterNumber;
    }
    const response = await this.client.get(
      `/api/rewrite/${taskId}/copyright`,
      { params }
    );
    return response.data;
  }

  /**
   * 获取原创性报告
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 原创性报告
   */
  async getOriginalityReport(taskId) {
    const response = await this.client.get(
      `/api/rewrite/${taskId}/originality`
    );
    return response.data;
  }
}

// 导出单例
module.exports = new ApiClient();
