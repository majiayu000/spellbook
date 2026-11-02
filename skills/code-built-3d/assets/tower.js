// Endless Tower: every object is a function that adds parts to an Assembly. The tower grows upward forever;
// each floor is a cut-away room with people, the neighbours are built band by band around it.
import { THREE, Assembly, rng } from './kit.js';

export const H = 3.4;                    // floor height
export const TW = 9, TD = 7;             // tower footprint (x, z)
export const BAND = 4;                   // floors per neighbour band
const X0 = -TW / 2, X1 = TW / 2, Z0 = -TD / 2, Z1 = TD / 2;
const V = (x, y, z) => new THREE.Vector3(x, y, z);

/* ---------- small things ---------- */
export function person(a, label, [x, y, z], { sit = false, rot = 0, shirt = 'light', hair = 'ink', reach = 0 } = {}) {
  const c = Math.cos(rot), s = Math.sin(rot);
  const P = (dx, dy, dz) => [x + dx * c + dz * s, y + dy, z - dx * s + dz * c];
  const o = (extra = {}) => ({ rot: [0, rot, 0], ...extra });
  if (sit) {
    a.box(`${label}·腿`, 0.38, 0.16, 0.5, o({ at: P(0, 0.42, 0.18), tone: 'dark' }));
    a.box(`${label}·小腿`, 0.36, 0.42, 0.14, o({ at: P(0, 0.02, 0.42), tone: 'dark' }));
  } else {
    a.box(`${label}·左腿`, 0.15, 0.8, 0.18, o({ at: P(-0.1, 0, 0), tone: 'dark' }));
    a.box(`${label}·右腿`, 0.15, 0.8, 0.18, o({ at: P(0.1, 0, 0), tone: 'dark' }));
  }
  const hip = sit ? 0.56 : 0.8;
  a.box(`${label}·上身`, 0.44, 0.62, 0.24, o({ at: P(0, hip, 0), tone: shirt }));
  a.box(`${label}·左臂`, 0.11, 0.56, 0.13, o({ at: P(-0.29, hip + 0.04, reach * 0.18), rot: [-reach, rot, 0.08], tone: shirt }));
  a.box(`${label}·右臂`, 0.11, 0.56, 0.13, o({ at: P(0.29, hip + 0.04, reach * 0.18), rot: [-reach, rot, -0.08], tone: shirt }));
  a.ball(`${label}·头`, 0.2, o({ at: P(0, hip + 0.86, 0), tone: 'white', detail: 1 }));
  a.box(`${label}·头发`, 0.38, 0.14, 0.34, o({ at: P(0, hip + 0.98, -0.03), tone: hair }));
  return V(...P(0, hip + 1.45, 0));
}
const chair = (a, [x, y, z], rot = 0) => {
  const c = Math.cos(rot), s = Math.sin(rot), P = (dx, dz) => [x + dx * c + dz * s, y, z - dx * s + dz * c];
  a.box('椅面', 0.5, 0.06, 0.5, { at: [...P(0, 0)].map((v, i) => i === 1 ? v + 0.44 : v), rot: [0, rot, 0], tone: 'mid' });
  a.box('椅背', 0.5, 0.5, 0.06, { at: [...P(0, -0.22)].map((v, i) => i === 1 ? v + 0.5 : v), rot: [0, rot, 0], tone: 'mid' });
  for (const [dx, dz] of [[-0.21, -0.21], [0.21, -0.21], [-0.21, 0.21], [0.21, 0.21]]) a.box('椅腿', 0.05, 0.44, 0.05, { at: P(dx, dz), rot: [0, rot, 0], tone: 'grey', edges: 0 });
};
const table = (a, label, [x, y, z], w, d, h = 0.76, tone = 'white') => {
  a.box(`${label}面`, w, 0.06, d, { at: [x, y + h - 0.06, z], tone });
  for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) a.box(`${label}腿`, 0.06, h - 0.06, 0.06, { at: [x + sx * (w / 2 - 0.08), y, z + sz * (d / 2 - 0.08)], tone: 'grey', edges: 0 });
};
const plant = (a, [x, y, z], r = rng(x * 7 + z)) => {
  a.cyl('花盆', 0.2, 0.32, { at: [x, y, z], tone: 'grey', r2: 0.24, seg: 8 });
  for (let i = 0; i < 3; i++) a.ball('叶丛', r.range(0.18, 0.28), { at: [x + r.range(-0.12, 0.12), y + 0.45 + i * 0.16, z + r.range(-0.12, 0.12)], tone: 'mid', detail: 0 });
};
const lamp = (a, [x, y, z], h = 1.5) => {
  a.cyl('灯座', 0.16, 0.04, { at: [x, y, z], tone: 'dark' });
  a.cyl('灯杆', 0.025, h, { at: [x, y, z], tone: 'dark', seg: 6, edges: 0 });
  a.cone('灯罩', 0.26, 0.3, { at: [x, y + h - 0.05, z], tone: 'white', seg: 10 });
};
const acUnit = (a, [x, y, z], rot = 0, role) => {
  a.box('空调外机', 0.8, 0.55, 0.36, { at: [x, y, z], rot: [0, rot, 0], tone: 'white', role });
  a.cyl('风扇罩', 0.19, 0.02, { at: [x + Math.sin(rot) * 0.19, y + 0.27, z + Math.cos(rot) * 0.19], rot: [Math.PI / 2, rot, 0], tone: 'grey', seg: 14, role });
};

/* ---------- rooms ---------- */
// Each room type: furnish(a, r) adds parts and returns people [{name, head}] with their thoughts.
const NAMES = ['阿梨', '老周', '小满', '禾禾', '阿鸣', '七七', '南风', '阿柚', '小葵', '老林', '桃子', '一一', '阿树', '十五', '米粒', '大海'];
export const ROOMS = {
  kitchen: { zh: '厨房', lines: ['汤还要再炖十分钟。', '盐放了吗？我忘了。', '今天的饺子包得最圆。'],
    furnish(a, r) {
      a.box('橱柜', 5.2, 0.88, 0.62, { at: [-1, 0, Z0 + 0.45], tone: 'white' });
      a.box('台面', 5.3, 0.06, 0.7, { at: [-1, 0.88, Z0 + 0.45], tone: 'mid' });
      a.box('吊柜', 3.6, 0.7, 0.36, { at: [-1.8, 1.85, Z0 + 0.3], tone: 'white' });
      a.box('灶台', 0.9, 0.04, 0.5, { at: [0.8, 0.94, Z0 + 0.45], tone: 'ink' });
      a.cyl('汤锅', 0.22, 0.3, { at: [0.6, 0.98, Z0 + 0.45], tone: 'grey', seg: 12 });
      a.box('冰箱', 0.82, 1.95, 0.72, { at: [X0 + 0.65, 0, Z0 + 0.5], tone: 'white' });
      a.box('冰箱门缝', 0.84, 0.02, 0.02, { at: [X0 + 0.65, 1.2, Z0 + 0.87], tone: 'ink', edges: 0 });
      table(a, '餐桌', [1.6, 0, 1.2], 1.7, 1, 0.76);
      chair(a, [1.1, 0, 2.05], Math.PI); chair(a, [2.1, 0, 2.05], Math.PI);
      a.box('碗', 0.24, 0.08, 0.24, { at: [1.4, 0.76, 1.1], tone: 'white' });
      plant(a, [X1 - 0.6, 0, Z0 + 0.6], r);
      const n1 = r.pick(NAMES), n2 = r.pick(NAMES.filter(n => n !== n1));
      return [{ name: n1, head: person(a, n1, [0.6, 0, Z0 + 1.25], { rot: Math.PI, reach: 0.5 }) }, { name: n2, head: person(a, n2, [2.1, 0, 2.05], { sit: true, rot: Math.PI, shirt: 'mid' }) }];
    } },
  workshop: { zh: '工作间', lines: ['这颗螺丝拆下来就别再丢了。', '先拍照，再拆下一层。', '弹簧都收进三号袋。'],
    furnish(a, r) {
      table(a, '工作台', [-0.6, 0, Z0 + 0.9], 4, 1.2, 0.9, 'mid');
      a.box('洞洞板', 3.6, 1.3, 0.05, { at: [-0.6, 1.25, Z0 + 0.22], tone: 'white' });
      for (let i = 0; i < 7; i++) a.box('挂着的工具', 0.08, r.range(0.3, 0.6), 0.04, { at: [-2.1 + i * 0.5, 1.6, Z0 + 0.27], tone: 'dark', edges: 0 });
      a.box('拆开的底板', 1.4, 0.04, 0.5, { at: [-0.9, 0.9, Z0 + 0.95], tone: 'grey' });
      for (let i = 0; i < 10; i++) for (let j = 0; j < 3; j++) a.box('键帽', 0.1, 0.06, 0.1, { at: [-1.5 + i * 0.13, 0.94, Z0 + 0.8 + j * 0.14], tone: 'white', edges: 0 });
      a.box('台钳', 0.3, 0.22, 0.26, { at: [0.9, 0.9, Z0 + 0.8], tone: 'dark' });
      lamp(a, [1.2, 0.9, Z0 + 1.2], 0.8);
      a.cyl('凳子', 0.24, 0.62, { at: [-0.6, 0, Z0 + 1.9], tone: 'grey', seg: 10 });
      a.box('零件柜', 1, 1.6, 0.5, { at: [X0 + 0.7, 0, 0.6], tone: 'white' });
      for (let i = 0; i < 4; i++) for (let j = 0; j < 3; j++) a.box('抽屉', 0.28, 0.3, 0.02, { at: [X0 + 0.38 + j * 0.32, 0.15 + i * 0.36, 0.86], tone: 'mid', edges: 0 });
      a.box('纸箱', 0.7, 0.5, 0.5, { at: [2.6, 0, 1.6], tone: 'grey' });
      a.box('纸箱', 0.5, 0.4, 0.4, { at: [2.6, 0.5, 1.6], tone: 'mid' });
      const n = r.pick(NAMES);
      return [{ name: n, head: person(a, n, [-0.6, 0, Z0 + 1.85], { sit: true, rot: Math.PI, reach: 0.7 }) }];
    } },
  study: { zh: '书房', lines: ['第三章写不下去，先泡杯茶。', '这本书借了三年还没还。', '明天一定早睡。'],
    furnish(a, r) {
      a.box('书架', 3.2, 2.4, 0.4, { at: [-1.6, 0, Z0 + 0.3], tone: 'white' });
      for (let row = 0; row < 4; row++) {
        a.box('隔板', 3.1, 0.04, 0.38, { at: [-1.6, 0.05 + row * 0.58, Z0 + 0.32], tone: 'mid', edges: 0 });
        let x = -3.1; while (x < -0.2) { const w = r.range(0.06, 0.14); a.box('书', w, r.range(0.32, 0.5), 0.28, { at: [x + w / 2, 0.09 + row * 0.58, Z0 + 0.34], tone: r.pick(['grey', 'mid', 'dark', 'light']), edges: 0 }); x += w + 0.015; }
      }
      table(a, '书桌', [1.6, 0, Z0 + 0.8], 2, 0.9, 0.76, 'white');
      a.box('显示器', 0.9, 0.55, 0.05, { at: [1.6, 0.9, Z0 + 0.5], tone: 'ink' });
      a.box('支架', 0.08, 0.14, 0.08, { at: [1.6, 0.76, Z0 + 0.52], tone: 'dark', edges: 0 });
      a.box('茶杯', 0.1, 0.12, 0.1, { at: [2.3, 0.76, Z0 + 0.9], tone: 'white' });
      chair(a, [1.6, 0, Z0 + 1.6], Math.PI);
      a.box('地毯', 3.4, 0.02, 2.2, { at: [0.3, 0, 1.2], tone: 'mid', edges: 0 });
      a.box('沙发座', 1.8, 0.42, 0.8, { at: [-1.5, 0, 2.2], tone: 'grey' });
      a.box('沙发背', 1.8, 0.5, 0.2, { at: [-1.5, 0.42, 2.5], tone: 'grey' });
      lamp(a, [X1 - 0.6, 0, 2.4], 1.6);
      const n = r.pick(NAMES);
      return [{ name: n, head: person(a, n, [1.6, 0, Z0 + 1.6], { sit: true, rot: Math.PI, reach: 0.6, shirt: 'white' }) }];
    } },
  greenhouse: { zh: '温室', lines: ['番茄今天红了一个。', '薄荷又长出盆了。', '浇水别浇到叶子上。'],
    furnish(a, r) {
      for (let row = 0; row < 2; row++) {
        a.box('种植箱', 6.4, 0.6, 0.9, { at: [-0.6, 0, Z0 + 0.7 + row * 2.1], tone: 'grey' });
        for (let i = 0; i < 8; i++) {
          const x = -3.5 + i * 0.82, z = Z0 + 0.7 + row * 2.1, t = r();
          if (t < 0.4) a.cone('幼苗', r.range(0.18, 0.3), r.range(0.5, 0.9), { at: [x, 0.6, z], tone: 'mid', seg: 6 });
          else a.ball('菜叶', r.range(0.22, 0.34), { at: [x, 0.82, z], tone: t < 0.7 ? 'mid' : 'light', detail: 0 });
        }
      }
      for (let i = 0; i < 3; i++) { a.cyl('吊灯线', 0.01, 0.9, { at: [-2.5 + i * 2.2, 2.2, -0.3], tone: 'ink', edges: 0, seg: 4 }); a.cone('吊灯', 0.3, 0.22, { at: [-2.5 + i * 2.2, 2.0, -0.3], tone: 'white', seg: 10 }); }
      a.cyl('喷壶', 0.16, 0.32, { at: [2.9, 0, 2.6], tone: 'white', seg: 10 });
      const n = r.pick(NAMES);
      return [{ name: n, head: person(a, n, [1.5, 0, 0.3], { rot: Math.PI * 0.95, reach: 0.9, shirt: 'mid' }) }];
    } },
  music: { zh: '乐室', lines: ['再练一遍就不弹错了。', '邻居今天没敲墙。', '这段慢一点更好听。'],
    furnish(a, r) {
      a.box('钢琴', 1.6, 1.25, 0.6, { at: [-1.6, 0, Z0 + 0.45], tone: 'ink' });
      a.box('琴键', 1.4, 0.04, 0.22, { at: [-1.6, 0.74, Z0 + 0.86], tone: 'white' });
      for (let i = 0; i < 12; i++) a.box('黑键', 0.05, 0.03, 0.12, { at: [-2.2 + i * 0.11, 0.78, Z0 + 0.82], tone: 'ink', edges: 0 });
      a.box('琴凳', 0.8, 0.46, 0.36, { at: [-1.6, 0, Z0 + 1.35], tone: 'dark' });
      a.box('音箱', 0.5, 1, 0.45, { at: [1.2, 0, Z0 + 0.5], tone: 'dark' });
      a.cyl('喇叭', 0.16, 0.02, { at: [1.2, 0.62, Z0 + 0.73], rot: [Math.PI / 2, 0, 0], tone: 'grey', seg: 14 });
      a.box('音箱', 0.5, 1, 0.45, { at: [2.6, 0, Z0 + 0.5], tone: 'dark' });
      a.line('谱架', [V(1.9, 0, 1.6), V(1.9, 1.2, 1.6), V(1.6, 1.4, 1.6), V(2.2, 1.4, 1.6), V(1.9, 1.2, 1.6)]);
      a.box('地毯', 2.6, 0.02, 1.8, { at: [1.2, 0, 1.7], tone: 'mid', edges: 0 });
      chair(a, [1.9, 0, 2.3], Math.PI);
      const n1 = r.pick(NAMES), n2 = r.pick(NAMES.filter(n => n !== n1));
      return [{ name: n1, head: person(a, n1, [-1.6, 0, Z0 + 1.35], { sit: true, rot: Math.PI, reach: 0.9 }) }, { name: n2, head: person(a, n2, [1.9, 0, 2.3], { sit: true, rot: Math.PI, shirt: 'white' }) }];
    } },
  server: { zh: '机房', lines: ['风扇声音小了，应该没事。', '第七台又在重启。', '今晚别再报警了。'],
    furnish(a, r) {
      for (let i = 0; i < 4; i++) {
        const x = -3 + i * 1.05;
        a.box('机柜', 0.9, 2.2, 0.9, { at: [x, 0, Z0 + 0.7], tone: 'dark' });
        for (let k = 0; k < 8; k++) a.box('服务器', 0.8, 0.16, 0.02, { at: [x, 0.25 + k * 0.24, Z0 + 1.16], tone: r.chance(0.2) ? 'white' : 'grey', edges: 0 });
      }
      a.line('走线槽', [V(-3.5, 2.6, Z0 + 0.7), V(1.2, 2.6, Z0 + 0.7), V(1.2, 2.6, 0.8)]);
      table(a, '值班桌', [2.4, 0, 1.4], 1.4, 0.8, 0.74, 'white');
      a.box('笔记本', 0.5, 0.03, 0.36, { at: [2.4, 0.74, 1.3], tone: 'grey' });
      chair(a, [2.4, 0, 2.1], Math.PI);
      a.box('空调柜', 0.7, 1.8, 0.5, { at: [X0 + 0.55, 0, 1.8], tone: 'white' });
      const n = r.pick(NAMES);
      return [{ name: n, head: person(a, n, [2.4, 0, 2.1], { sit: true, rot: Math.PI, reach: 0.6, shirt: 'grey' }) }];
    } },
  laundry: { zh: '洗衣房', lines: ['袜子又少了一只。', '这件毛衣别放烘干。', '还剩二十分钟。'],
    furnish(a, r) {
      for (let i = 0; i < 3; i++) {
        a.box('洗衣机', 0.8, 0.9, 0.7, { at: [-2.6 + i * 0.95, 0, Z0 + 0.5], tone: 'white' });
        a.cyl('滚筒门', 0.26, 0.03, { at: [-2.6 + i * 0.95, 0.45, Z0 + 0.86], rot: [Math.PI / 2, 0, 0], tone: 'grey', seg: 16 });
      }
      a.line('晾衣绳', [V(-0.8, 2.3, 0.4), V(3.6, 2.3, 0.4)]);
      for (let i = 0; i < 6; i++) a.box('晾着的衣服', r.range(0.3, 0.55), r.range(0.4, 0.7), 0.03, { at: [-0.4 + i * 0.7, 1.6, 0.4], tone: r.pick(['white', 'mid', 'grey']), edges: 0 });
      a.cyl('洗衣篮', 0.32, 0.4, { at: [1.6, 0, 2.2], tone: 'mid', seg: 10 });
      a.box('长凳', 1.6, 0.42, 0.4, { at: [-1.8, 0, 2.3], tone: 'grey' });
      const n = r.pick(NAMES);
      return [{ name: n, head: person(a, n, [-1.8, 0, 2.3], { sit: true, rot: Math.PI, shirt: 'white' }) }];
    } },
};
const TYPES = Object.keys(ROOMS);
// Neighbouring floors never repeat: consecutive indices differ by 2–4 (mod 7).
export function roomType(n) { return TYPES[(((n * 3 + (rng(n * 977 + 13)() < 0.5 ? 0 : 1)) % TYPES.length) + TYPES.length) % TYPES.length]; }

/* ---------- one tower floor ---------- */
// Returns structure (always drawn), shell (front walls that can be cut away) and furniture (exploded on demand).
export function floorParts(n, look) {
  const r = rng(`floor-${n}`), type = roomType(n), room = ROOMS[type];
  const st = new Assembly(`${n}F 结构`, look), sh = new Assembly(`${n}F 外墙`, look), fu = new Assembly(`${n}F ${room.zh}`, look);
  // slab and back walls
  st.box('楼板', TW + 0.3, 0.26, TD + 0.3, { at: [0, -0.26, 0], tone: 'white' });
  st.box('后墙', TW, H - 0.26, 0.18, { at: [0, 0, Z0 + 0.09], tone: 'light' });
  st.box('侧墙', 0.18, H - 0.26, TD, { at: [X0 + 0.09, 0, 0], tone: 'light' });
  for (let i = 0; i < 3; i++) st.box('后窗', 1.3, 1.2, 0.04, { at: [-3 + i * 3, 1.05, Z0 + 0.2], tone: 'grey', edges: 25 });
  st.box('立柱', 0.3, H - 0.26, 0.3, { at: [X1 - 0.15, 0, Z1 - 0.15], tone: 'white' });
  st.box('楼板边', TW + 0.34, 0.12, 0.06, { at: [0, -0.26, Z1 + 0.18], tone: 'mid', edges: 0 });
  // shell: front (+z) and side (+x) walls with windows, cut away when the camera looks in
  // Each wall is one slab with window panes set proud of it: fewer seams, the way an illustrator draws it.
  const sill = 0.9, wh = 1.5;
  sh.box('前墙', TW, H - 0.26, 0.16, { at: [0, 0, Z1 - 0.08], role: 'shell', tone: 'light' });
  for (let i = 0; i < 3; i++) {
    const x = -3 + i * 3;
    sh.box('窗', 1.5, wh, 0.04, { at: [x, sill, Z1 + 0.02], role: 'shell', tone: r.chance(0.25) ? 'grey' : 'white' });
    sh.box('窗台', 1.7, 0.08, 0.14, { at: [x, sill - 0.08, Z1 + 0.06], role: 'shell', tone: 'white', edges: 30 });
  }
  sh.box('侧墙', 0.16, H - 0.26, TD, { at: [X1 - 0.08, 0, 0], role: 'shell', tone: 'light' });
  for (const z of [Z0 + 1.6, Z1 - 1.6]) sh.box('窗', 0.04, wh, 1.0, { at: [X1 + 0.02, sill, z], role: 'shell', tone: 'white' });
  if (r.chance(0.45)) acUnit(sh, [r.pick([-3, 0, 3]) + 0.9, 0.3, Z1 + 0.2], 0, 'shell');
  if (r.chance(0.25)) { // balcony on the front
    st.box('阳台', 3, 0.14, 1.1, { at: [-3, -0.14, Z1 + 0.55], tone: 'white' });
    st.line('阳台栏杆', [V(-4.5, 1, Z1), V(-4.5, 1, Z1 + 1.1), V(-1.5, 1, Z1 + 1.1), V(-1.5, 1, Z1)]);
    for (let i = 0; i <= 10; i++) st.line('栏杆', [V(-4.5 + i * 0.3, 0, Z1 + 1.1), V(-4.5 + i * 0.3, 1, Z1 + 1.1)]);
    plant(st, [-2.1, 0, Z1 + 0.6], r);
  }
  // elevator shaft frame on the +x side
  const sx0 = X1 + 0.3, sx1 = X1 + 2.7, sz = 1.3;
  for (const [x, z] of [[sx0, -sz], [sx1, -sz], [sx0, sz], [sx1, sz]]) st.box('井道立柱', 0.12, H, 0.12, { at: [x, -0.26, z], tone: 'mid', edges: 25 });
  st.line('井道横梁', [V(sx0, -0.1, -sz), V(sx1, -0.1, -sz), V(sx1, -0.1, sz), V(sx0, -0.1, sz), V(sx0, -0.1, -sz)]);
  st.line('井道斜撑', [V(sx1, -0.1, sz), V(sx1, H - 0.4, -sz)]);
  st.box('电梯厅', 2.4, 0.14, 2.6, { at: [X1 + 1.5, -0.26, 0], tone: 'white' });
  const people = room.furnish(fu, r).map((p, i) => ({ ...p, line: room.lines[(n + i) % room.lines.length] }));
  return { n, type, zh: room.zh, st, sh, fu, people };
}

export function cab(look) {
  const a = new Assembly('电梯轿厢', look), w = 2.1, h = 2.7;
  a.box('轿厢底', w, 0.12, w, { at: [0, 0, 0], tone: 'white' });
  a.box('轿厢顶', w, 0.16, w, { at: [0, h, 0], tone: 'white' });
  a.box('后壁', 0.08, h, w, { at: [-w / 2 + 0.04, 0, 0], tone: 'light' });
  a.box('侧壁', w, h, 0.08, { at: [0, 0, -w / 2 + 0.04], tone: 'light' });
  for (const [x, z] of [[w / 2, w / 2], [w / 2, -w / 2], [-w / 2, w / 2]]) a.box('轿厢框', 0.08, h, 0.08, { at: [x - Math.sign(x) * 0.04, 0, z - Math.sign(z) * 0.04], tone: 'mid' });
  a.box('机箱', 1, 0.3, 0.8, { at: [0, h + 0.16, 0], tone: 'grey' });
  a.line('钢缆', [V(0, h + 0.46, 0), V(0, h + 40, 0)]);
  a.line('扶手', [V(-0.95, 0.95, -0.9), V(0.9, 0.95, -0.9)]);
  const head = person(a, '乘客', [0.1, 0.12, 0.2], { rot: Math.PI * 0.25, shirt: 'white' });
  return { a, head };
}

/* ---------- neighbours, built band by band ---------- */
const SLOTS = [
  { x: -17, z: -5, w: [7, 11], d: [7, 10] }, { x: -4, z: -19, w: [8, 12], d: [6, 9] }, { x: 10, z: -16, w: [6, 9], d: [6, 9] },
  { x: -21, z: 7, w: [6, 9], d: [6, 8] }, { x: -30, z: -22, w: [9, 13], d: [9, 13] },
  { x: 6, z: -33, w: [9, 12], d: [8, 12] },
];
function footprint(slot, band) { const r = rng(`fp-${slot}-${band}`), s = SLOTS[slot]; return { w: r.range(...s.w), d: r.range(...s.d), tone: r.pick(['white', 'white', 'light']) }; }

export function bandParts(b, look) {
  const a = new Assembly(`第 ${b} 段`, look), bh = H * BAND, y0 = b * bh, r = rng(`band-${b}`);
  SLOTS.forEach((s, i) => {
    const f = footprint(i, b), up = footprint(i, b + 1), x0 = s.x - f.w / 2, x1 = s.x + f.w / 2, z0 = s.z - f.d / 2, z1 = s.z + f.d / 2;
    a.box('楼体', f.w, bh, f.d, { at: [s.x, y0, s.z], tone: f.tone });
    a.box('檐口', f.w + 0.3, 0.3, f.d + 0.3, { at: [s.x, y0 + bh - 0.3, s.z], tone: 'white' });
    const cols = Math.max(2, Math.floor(f.w / 1.6)), rows = BAND, deep = Math.max(2, Math.floor(f.d / 1.6));
    const style = rng(`style-${i}-${b}`).pick(['grid', 'grid', 'ribbon', 'fins', 'balcony']);
    for (let k = 0; k < rows; k++) {
      const y = y0 + k * H + 0.9;
      if (style === 'ribbon') { // continuous strip windows with a sill band
        a.box('带形窗', f.w - 0.6, 1.1, 0.06, { at: [s.x, y, z1 + 0.02], tone: 'mid', edges: 30 });
        a.box('带形窗', 0.06, 1.1, f.d - 0.6, { at: [x1 + 0.02, y, s.z], tone: 'grey', edges: 30 });
        a.box('窗台线', f.w + 0.1, 0.12, 0.2, { at: [s.x, y - 0.12, z1 + 0.05], tone: 'white', edges: 30 });
        continue;
      }
      for (let c = 0; c < cols; c++) {
        const x = x0 + (c + 0.5) * f.w / cols;
        a.box('窗', 0.9, 1.3, 0.06, { at: [x, y, z1 + 0.02], tone: r.chance(0.08) ? 'dark' : 'light', edges: 30 });
        if (style === 'balcony' && c % 2 === 0) { a.box('小阳台', 1.3, 0.1, 0.6, { at: [x, y - 0.45, z1 + 0.3], tone: 'white' }); a.line('阳台栏杆', [V(x - 0.65, y + 0.35, z1 + 0.6), V(x + 0.65, y + 0.35, z1 + 0.6)]); }
      }
      for (let c = 0; c < deep; c++) a.box('窗', 0.06, 1.3, 0.9, { at: [x1 + 0.02, y, z0 + (c + 0.5) * f.d / deep], tone: r.chance(0.08) ? 'dark' : 'mid', edges: 30 });
      if (r.chance(0.35)) acUnit(a, [x0 + r.int(0, cols - 1) * f.w / cols + 0.6, y - 0.6, z1 + 0.2]);
    }
    if (style === 'fins') for (let c = 0; c <= cols; c++) a.box('竖向遮阳板', 0.12, bh, 0.45, { at: [x0 + c * f.w / cols, y0, z1 + 0.22], tone: 'white', edges: 30 });
    if (r.chance(0.5)) { // fire-escape ladder on the +x face
      const z = z0 + f.d * 0.25;
      a.line('爬梯', [V(x1 + 0.3, y0, z - 0.25), V(x1 + 0.3, y0 + bh, z - 0.25)]);
      a.line('爬梯', [V(x1 + 0.3, y0, z + 0.25), V(x1 + 0.3, y0 + bh, z + 0.25)]);
      for (let y = y0 + 0.3; y < y0 + bh; y += 0.35) a.line('梯级', [V(x1 + 0.3, y, z - 0.25), V(x1 + 0.3, y, z + 0.25)]);
    }
    if (r.chance(0.5)) a.cyl('落水管', 0.07, bh, { at: [x0 + 0.3, y0, z1 + 0.12], tone: 'white', seg: 6 });
    // a ledge where the next band steps in: terrace clutter
    if (up.w < f.w - 1 || up.d < f.d - 1) {
      const top = y0 + bh, r2 = rng(`roof-${i}-${b}`);
      if (r2.chance(0.7)) { a.cyl('水箱', 0.7, 1.2, { at: [x1 - 1, top + 0.9, z1 - 1], tone: 'white', seg: 12 }); for (const [dx, dz] of [[-0.45, -0.45], [0.45, -0.45], [-0.45, 0.45], [0.45, 0.45]]) a.box('水箱支架', 0.08, 0.9, 0.08, { at: [x1 - 1 + dx, top, z1 - 1 + dz], tone: 'grey', edges: 0 }); }
      for (let k = 0; k < r2.int(1, 3); k++) acUnit(a, [x0 + 1 + k * 1.1, top, z1 - 0.6]);
      a.box('通风箱', 0.9, 0.6, 0.7, { at: [s.x, top, z1 - 0.8], tone: 'grey' });
      a.line('天台栏杆', [V(x0, top + 0.9, z1), V(x1, top + 0.9, z1), V(x1, top + 0.9, z0)]);
      if (r2.chance(0.4)) a.cyl('天线', 0.03, 2.4, { at: [x0 + 0.6, top, z0 + 0.6], tone: 'dark', seg: 4 });
    }
  });
  // skybridge from the tower to the first neighbour, and sagging cables
  for (let k = 0; k < BAND; k++) {
    const fl = b * BAND + k, rr = rng(`bridge-${fl}`);
    if (rr.chance(0.14)) {
      const y = fl * H, x0 = SLOTS[0].x + footprint(0, b).w / 2;
      a.box('连廊', X0 - x0, 0.2, 1.8, { at: [(x0 + X0) / 2, y - 0.2, -0.6], tone: 'white' });
      for (const z of [-1.5, 0.3]) a.line('连廊栏杆', [V(x0, y + 1, z), V(X0, y + 1, z)]);
      for (let x = x0; x < X0; x += 0.8) a.line('连廊桁架', [V(x, y - 0.2, 0.3), V(x + 0.4, y - 0.9, 0.3), V(x + 0.8, y - 0.2, 0.3)]);
    }
  }
  for (let k = 0; k < 2; k++) {
    const rr = rng(`cable-${b}-${k}`), y = y0 + rr.range(1, bh - 1), s = SLOTS[rr.int(0, 2)];
    const A = V(X0, y, Z0 + 0.5), B = V(s.x + 2, y + rr.range(-1, 1), s.z + 2), pts = [];
    for (let t = 0; t <= 1.0001; t += 0.1) pts.push(A.clone().lerp(B, t).add(V(0, -Math.sin(t * Math.PI) * 1.2, 0)));
    a.line('电缆', pts);
  }
  return a;
}
