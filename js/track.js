/* 无忧睡眠国内官网 · 访问埋点
 * ------------------------------------------------------------------
 * 目的：百度推送了 69 条 URL，但一直不知道到底有没有人从搜索进来。
 *       没有埋点时，"没人来"和"来了没留资"是同一件事，无法区分。
 *
 * 做法：页面加载后异步写一行到云数据库 domestic_visits。
 *   ① 只记 HTML 页面（本脚本只被页面引用，静态资源不触发）
 *   ② 同一会话同一路径只记一次（sessionStorage），避免刷新刷量
 *   ③ 跳过明显爬虫 UA
 *   ④ 用 fetch + keepalive，失败静默，绝不影响页面
 *   ⑤ 不存 IP、不存任何个人信息
 *
 * 2026-10-19 立
 */
(function () {
  'use strict';
  try {
    var API = 'https://wuyousleep.net/.cloud/database/rest/domestic_visits';
    var KEY = 'wbpk_Fu5j2M97m76woNurF1iUSc_m0ND2W6BP5CP4iOB2LbqMTKh7NXvwg98';

    var ua = (navigator.userAgent || '').slice(0, 160);
    if (!ua) return;
    if (/bot|crawler|spider|slurp|facebookexternalhit|preview|headless|phantom|curl|wget|python-requests/i.test(ua)) return;

    // 同一会话同一页只记一次
    var key = 'dsv:' + location.pathname;
    try {
      if (sessionStorage.getItem(key) === '1') return;
      sessionStorage.setItem(key, '1');
    } catch (e) { }

    // 来源判定
    var ref = (document.referrer || '').slice(0, 300);
    var src = 'direct';
    if (!ref) {
      src = 'direct';
    } else if (/baidu\.com/i.test(ref)) {
      src = 'baidu';
    } else if (/weixin|wechat|qq\.com/i.test(ref)) {
      src = 'weixin';
    } else if (/sogou\.com/i.test(ref)) {
      src = 'sogou';
    } else if (/so\.com/i.test(ref)) {
      src = '360';
    } else if (/bing\.com/i.test(ref)) {
      src = 'bing';
    } else if (ref.indexOf('shuimian.xyz') >= 0) {
      src = 'internal';
    } else {
      src = 'other';
    }

    var row = {
      path: location.pathname.slice(0, 200),
      ref: ref || null,
      ref_src: src,
      ua: ua,
      device: /Mobile|Android|iPhone|iPad|iPod/i.test(ua) ? 'mobile' : 'desktop'
    };

    fetch(API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-wb-webapp-access-key': KEY
      },
      body: JSON.stringify(row),
      keepalive: true,
      mode: 'cors'
    }).catch(function () { });
  } catch (e) {
    /* 静默 */
  }
})();
