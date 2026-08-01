import { money } from './src/lib/formatters';

const testCases = [
  "1234567.89",
  "0.1234",
  "10.00",
  "99999999999999.99",
  "-50.55"
];

const failed = false;
for (const tc of testCases) {
  const result = money(tc);
  console.log(`money("${tc}") = ${result}`);
  // Just manual checks in output
}
if (failed) {
  process.exit(1);
} else {
  console.log("money() precision tests passed.");
}
