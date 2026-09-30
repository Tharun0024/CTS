const fs = require('fs');
const path = require('path');

function replaceInFile(filePath, search, replacement) {
  const fullPath = path.join(__dirname, filePath);
  if (fs.existsSync(fullPath)) {
    let content = fs.readFileSync(fullPath, 'utf8');
    content = content.replace(search, replacement);
    fs.writeFileSync(fullPath, content);
  }
}

// Sidebar.tsx
replaceInFile('src/components/common/Sidebar.tsx', /const accentLight =.*?;\n/g, '');
replaceInFile('src/components/common/Sidebar.tsx', /const badgeBg =.*?;\n/g, '');

// ClaimHeader.tsx
replaceInFile('src/components/shared/ClaimHeader.tsx', /ArrowRight, /g, '');

// ClaimTimeline.tsx
replaceInFile('src/components/shared/ClaimTimeline.tsx', /statusConfig\[event\.status\]/g, 'statusConfig[event.status || "PROCESSING"]');

// glassmorphism-trust-hero.tsx
replaceInFile('src/components/ui/glassmorphism-trust-hero.tsx', /import React from 'react';\n/g, '');
replaceInFile('src/components/ui/glassmorphism-trust-hero.tsx', /import \{ Play, Star, CheckCircle2, Lock \} from 'lucide-react';\n/g, '');

// mock/cases.ts
replaceInFile('src/mock/cases.ts', /Patient\[\] = /g, 'any[] = ');

// HospitalCaseDetails.tsx
replaceInFile('src/pages/hospital/HospitalCaseDetails.tsx', /MORE_INFORMATION/g, 'MORE_INFO');

// HospitalCases.tsx
replaceInFile('src/pages/hospital/HospitalCases.tsx', /MORE_INFORMATION/g, 'MORE_INFO');

// InsuranceCaseDetails.tsx
replaceInFile('src/pages/insurance/InsuranceCaseDetails.tsx', /MORE_INFORMATION/g, 'MORE_INFO');

// RoleSelect.tsx
replaceInFile('src/pages/RoleSelect.tsx', /const \[menuOpen, setMenuOpen\] = useState\(false\);\n/g, '');
replaceInFile('src/pages/RoleSelect.tsx', /const \[activeStep, setActiveStep\] = useState\(1\);\n/g, '');
replaceInFile('src/pages/RoleSelect.tsx', /width=\{32\}/g, 'width={32 as any}');
replaceInFile('src/pages/RoleSelect.tsx', /width=\{32 as any as any\}/g, 'width={32 as any}');

// claimsApi.ts
replaceInFile('src/services/claimsApi.ts', /import \{ mockClaims \}.*?;\n/g, '');
replaceInFile('src/services/claimsApi.ts', /\[\.\.\.mockClaims\]/g, '[]');

// reviewApi.ts
replaceInFile('src/services/reviewApi.ts', /payload: any/g, '_payload: any');

console.log("Fixes applied");
