// The program on screen in the film. Run it: bun last-bug-demo.js
// The missing semicolon glues the two lines into sum(items)[first, last] = ends(items).
const sum = xs => xs.reduce((a, b) => a + b, 0)
const ends = xs => [xs[0], xs[xs.length - 1]]

function report(items) {
  let first, last
  const total = sum(items)
  [first, last] = ends(items)
  return { total, first, last }
}

function fixed(items) {
  let first, last
  const total = sum(items);
  [first, last] = ends(items)
  return { total, first, last }
}

function test(fn) {
  const r = (() => fn([1, 2, 3]))()
  return r.total === 6 && r.first === 1 && r.last === 3
}

function runSuite(fn) {
  return test(fn)
}

function main(fn) {
  try {
    return runSuite(fn) ? 'all tests passed' : '1 failed'
  } catch (e) {
    console.log(e.stack.split('\n').slice(1).map(l => l.trim()).join('\n'))
    return '1 failed'
  }
}

console.log('without the semicolon:', main(report))
console.log('with the semicolon:   ', main(fixed))
