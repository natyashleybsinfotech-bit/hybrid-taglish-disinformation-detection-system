// Assembler: combines all section modules into one children array
const sec1Mod = require('./sdd_sec1.js');
const sec2Mod = require('./sdd_sec2.js');
const sec3Mod = require('./sdd_sec3.js');
const sec4Mod = require('./sdd_sec4.js');
const sec56Mod = require('./sdd_sec56.js');
const sec78Mod = require('./sdd_sec78.js');
const { Paragraph, PageBreak } = require('docx');

module.exports = {
  buildAll(h) {
    const s1 = sec1Mod(h);
    const s2 = sec2Mod(h);
    const s3 = sec3Mod(h);
    const s4 = sec4Mod(h);
    const s56 = sec56Mod(h);
    const s78 = sec78Mod(h);

    const pb = new Paragraph({ children: [new PageBreak()] });

    return [
      ...s1.coverPage(),
      ...s1.sec1(),
      pb,
      ...s2.sec2(),
      pb,
      ...s3.sec3(),
      pb,
      ...s4.sec4(),
      pb,
      ...s56.sec5(),
      pb,
      ...s56.sec6(),
      pb,
      ...s78.sec7(),
      pb,
      ...s78.sec8(),
    ];
  }
};
