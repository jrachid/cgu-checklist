import { defineConfig } from 'wxt';

export default defineConfig({
  manifest: {
    name: 'CGU Checklist',
    description: "Résume les points cruciaux des CGU au moment où l'on vous demande de les accepter.",
    // Le script de fond doit pouvoir télécharger la page des CGU de n'importe quel site.
    host_permissions: ['<all_urls>'],
  },
});
