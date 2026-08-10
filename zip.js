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

  /**
   * SongScope自身が作る store-method ZIP を読みます。
   * 復元用途なので central directory / local header / CRC32 を照合し、
   * encryption / compression / ZIP64 は受け付けません。
   * @param {Blob|ArrayBuffer|Uint8Array} source
   * @returns {Promise<Map<string,Uint8Array>>}
   */
  async function readZip(source) {
    var ab;
    if (source instanceof ArrayBuffer) ab = source;
    else if (source instanceof Uint8Array) ab = source.buffer.slice(source.byteOffset, source.byteOffset + source.byteLength);
    else if (source && typeof source.arrayBuffer === 'function') ab = await source.arrayBuffer();
    else throw new Error('ZIPを読み込めません');
    var u8 = new Uint8Array(ab);
    var dv = new DataView(ab);
    if (u8.length < 22) throw new Error('ZIPが短すぎます');

    var eocd = -1;
    var min = Math.max(0, u8.length - 22 - 65535);
    for (var i = u8.length - 22; i >= min; i--) {
      if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    }
    if (eocd < 0) throw new Error('ZIPのEOCDが見つかりません');
    var diskNo = dv.getUint16(eocd + 4, true);
    var cdDisk = dv.getUint16(eocd + 6, true);
    var entriesDisk = dv.getUint16(eocd + 8, true);
    var entriesTotal = dv.getUint16(eocd + 10, true);
    var cdSize = dv.getUint32(eocd + 12, true);
    var cdOffset = dv.getUint32(eocd + 16, true);
    if (diskNo !== 0 || cdDisk !== 0 || entriesDisk !== entriesTotal) throw new Error('multi-disk ZIPは未対応です');
    if (entriesTotal === 0xFFFF || cdSize === 0xFFFFFFFF || cdOffset === 0xFFFFFFFF) throw new Error('ZIP64は未対応です');
    if (cdOffset + cdSize > u8.length) throw new Error('ZIP central directoryが範囲外です');

    var dec = new TextDecoder('utf-8');
    var out = new Map();
    var pos = cdOffset;
    for (var n = 0; n < entriesTotal; n++) {
      if (pos + 46 > u8.length || dv.getUint32(pos, true) !== 0x02014b50) throw new Error('ZIP central headerが不正です');
      var flags = dv.getUint16(pos + 8, true);
      var method = dv.getUint16(pos + 10, true);
      var crc = dv.getUint32(pos + 16, true);
      var compSize = dv.getUint32(pos + 20, true);
      var uncompSize = dv.getUint32(pos + 24, true);
      var nameLen = dv.getUint16(pos + 28, true);
      var extraLen = dv.getUint16(pos + 30, true);
      var commentLen = dv.getUint16(pos + 32, true);
      var localOffset = dv.getUint32(pos + 42, true);
      if ((flags & 0x0001) !== 0) throw new Error('暗号化ZIPは未対応です');
      if (method !== 0) throw new Error('圧縮ZIPは未対応です。SongScope完全バックアップZIPを選択してください');
      if (compSize !== uncompSize) throw new Error('ZIPサイズ情報が不正です');
      if (pos + 46 + nameLen + extraLen + commentLen > u8.length) throw new Error('ZIP central entryが範囲外です');
      var name = dec.decode(u8.slice(pos + 46, pos + 46 + nameLen));

      if (localOffset + 30 > u8.length || dv.getUint32(localOffset, true) !== 0x04034b50) throw new Error('ZIP local headerが不正です');
      var localMethod = dv.getUint16(localOffset + 8, true);
      var localNameLen = dv.getUint16(localOffset + 26, true);
      var localExtraLen = dv.getUint16(localOffset + 28, true);
      if (localMethod !== method) throw new Error('ZIP methodが一致しません');
      var dataStart = localOffset + 30 + localNameLen + localExtraLen;
      var dataEnd = dataStart + compSize;
      if (dataEnd > u8.length) throw new Error('ZIP entry dataが範囲外です');
      var data = u8.slice(dataStart, dataEnd);
      if (crc32(data) !== crc) throw new Error('ZIP CRC32が一致しません: ' + name);
      if (out.has(name)) throw new Error('ZIP内に重複ファイル名があります: ' + name);
      out.set(name, data);
      pos += 46 + nameLen + extraLen + commentLen;
    }
    return out;
  }

  global.SongScopeZip = { createZip: createZip, readZip: readZip, crc32: crc32 };
})(self);
