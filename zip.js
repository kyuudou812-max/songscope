/* SongScope minimal ZIP writer (store / 無圧縮)
 * 外部通信は一切行いません。ZIP仕様(APPNOTE 6.3.x)のうち、
 * ローカルヘッダ + セントラルディレクトリ + EOCD だけを使用します。
 * PNG/CSV/MD/JSON をそのまま格納するため圧縮は行いません（実装を単純・確実にするため）。
 */
(function (global) {
  'use strict';

  var CRC_TABLE = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) {
      var c = n;
      for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      t[n] = c >>> 0;
    }
    return t;
  })();

  function crc32(u8) {
    var c = 0xFFFFFFFF;
    for (var i = 0; i < u8.length; i++) c = CRC_TABLE[(c ^ u8[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  function dosDateTime(d) {
    var time = ((d.getHours() & 31) << 11) | ((d.getMinutes() & 63) << 5) | ((d.getSeconds() / 2) & 31);
    var date = (((d.getFullYear() - 1980) & 127) << 9) | (((d.getMonth() + 1) & 15) << 5) | (d.getDate() & 31);
    return { time: time, date: date };
  }

  var enc = new TextEncoder();

  /**
   * @param {Array<{name:string, data:Uint8Array|string}>} files
   * @returns {Blob} application/zip
   */
  function createZip(files) {
    var entries = files.map(function (f) {
      var data = typeof f.data === 'string' ? enc.encode(f.data) : f.data;
      return { nameBytes: enc.encode(f.name), data: data, crc: crc32(data) };
    });
    var dt = dosDateTime(new Date());
    var parts = [];
    var offset = 0;
    var central = [];

    entries.forEach(function (e) {
      var lh = new Uint8Array(30 + e.nameBytes.length);
      var v = new DataView(lh.buffer);
      v.setUint32(0, 0x04034b50, true);
      v.setUint16(4, 20, true);        // version needed
      v.setUint16(6, 0x0800, true);    // UTF-8 filename flag
      v.setUint16(8, 0, true);         // method: store
      v.setUint16(10, dt.time, true);
      v.setUint16(12, dt.date, true);
      v.setUint32(14, e.crc, true);
      v.setUint32(18, e.data.length, true);
      v.setUint32(22, e.data.length, true);
      v.setUint16(26, e.nameBytes.length, true);
      v.setUint16(28, 0, true);
      lh.set(e.nameBytes, 30);
      parts.push(lh, e.data);

      var ch = new Uint8Array(46 + e.nameBytes.length);
      var cv = new DataView(ch.buffer);
      cv.setUint32(0, 0x02014b50, true);
      cv.setUint16(4, 20, true);
      cv.setUint16(6, 20, true);
      cv.setUint16(8, 0x0800, true);
      cv.setUint16(10, 0, true);
      cv.setUint16(12, dt.time, true);
      cv.setUint16(14, dt.date, true);
      cv.setUint32(16, e.crc, true);
      cv.setUint32(20, e.data.length, true);
      cv.setUint32(24, e.data.length, true);
      cv.setUint16(28, e.nameBytes.length, true);
      cv.setUint32(42, offset, true);
      ch.set(e.nameBytes, 46);
      central.push(ch);

      offset += lh.length + e.data.length;
    });

    var centralSize = central.reduce(function (a, c) { return a + c.length; }, 0);
    var eocd = new Uint8Array(22);
    var ev = new DataView(eocd.buffer);
    ev.setUint32(0, 0x06054b50, true);
    ev.setUint16(8, entries.length, true);
    ev.setUint16(10, entries.length, true);
    ev.setUint32(12, centralSize, true);
    ev.setUint32(16, offset, true);

    return new Blob(parts.concat(central, [eocd]), { type: 'application/zip' });
  }

  global.SongScopeZip = { createZip: createZip, crc32: crc32 };
})(self);
