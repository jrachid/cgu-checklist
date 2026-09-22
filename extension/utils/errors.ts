interface ValidationError {
  loc: (string | number)[];
  msg: string;
}

// FastAPI rend `detail` en texte pour nos erreurs, et en liste quand la requête n'a pas le format attendu.
export function describeError(status: number, detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const fields = (detail as ValidationError[]).map((e) => `${e.loc.slice(1).join('.')} : ${e.msg}`).join(' ; ');
    return `Le serveur d'analyse refuse le format de la requête (${fields}). L'extension et le serveur n'ont sans doute pas la même version : recharge l'extension dans chrome://extensions.`;
  }
  return `Le serveur d'analyse a répondu ${status}`;
}
