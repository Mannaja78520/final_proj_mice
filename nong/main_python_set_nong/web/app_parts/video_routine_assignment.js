// Rectangular Hungarian assignment: bounded polynomial work even when many
// similar dancers and camera fragments make every local match ambiguous.
class VideoRoutineAssignment {
  static solve(matrix, forbiddenRow = -1, forbiddenColumn = -1) {
    const rows = matrix.length, columns = matrix[0]?.length || 0, large = 1e12;
    if (!rows) return { cost: 0, columns: [] };
    if (columns < rows || matrix.some(row => row.length !== columns)) throw new Error('Incomplete routine assignment matrix');
    const u = new Float64Array(rows + 1), v = new Float64Array(columns + 1);
    const matched = new Int32Array(columns + 1), way = new Int32Array(columns + 1);
    const value = (i, j) => (i === forbiddenRow && j === forbiddenColumn) || !Number.isFinite(matrix[i][j]) ? large : matrix[i][j];
    for (let row = 1; row <= rows; row++) {
      matched[0] = row;
      const minimum = new Float64Array(columns + 1).fill(large), used = new Uint8Array(columns + 1);
      let column = 0;
      do {
        used[column] = 1;
        const current = matched[column]; let delta = large, next = 0;
        for (let j = 1; j <= columns; j++) if (!used[j]) {
          const cost = value(current - 1, j - 1) - u[current] - v[j];
          if (cost < minimum[j]) { minimum[j] = cost; way[j] = column; }
          if (minimum[j] < delta) { delta = minimum[j]; next = j; }
        }
        if (delta >= large / 2) return { cost: Infinity, columns: [] };
        for (let j = 0; j <= columns; j++) {
          if (used[j]) { u[matched[j]] += delta; v[j] -= delta; }
          else minimum[j] -= delta;
        }
        column = next;
      } while (matched[column]);
      do { const previous = way[column]; matched[column] = matched[previous]; column = previous; } while (column);
    }
    const result = Array(rows).fill(-1);
    for (let j = 1; j <= columns; j++) if (matched[j]) result[matched[j] - 1] = j - 1;
    const cost = result.reduce((sum, column, row) => sum + value(row, column), 0);
    return { cost: cost >= large / 2 ? Infinity : cost, columns: result };
  }
}
