const fs = require('fs');
const path = require('path');

function replaceInFile(filePath, regex, replacement) {
  const fullPath = path.join(__dirname, filePath);
  if (fs.existsSync(fullPath)) {
    let content = fs.readFileSync(fullPath, 'utf8');
    content = content.replace(regex, replacement);
    fs.writeFileSync(fullPath, content);
  }
}

// Sidebar.tsx
replaceInFile('src/components/common/Sidebar.tsx', /const accentLight =.*?\n/g, '');
replaceInFile('src/components/common/Sidebar.tsx', /const badgeBg =.*?\n/g, '');

// ClaimForm.tsx
replaceInFile('src/components/hospital/ClaimForm.tsx', /FileText, /g, '');

// ClaimsTable.tsx
replaceInFile('src/components/hospital/ClaimsTable.tsx', /const accentBorder =.*?\n/g, '');

// ReviewQueueTable.tsx (PENDING to SUBMITTED)
replaceInFile('src/components/insurance/ReviewQueueTable.tsx', /'PENDING'/g, "'SUBMITTED'");

// ClaimHeader.tsx
replaceInFile('src/components/shared/ClaimHeader.tsx', /Calendar, /, '');
replaceInFile('src/components/shared/ClaimHeader.tsx', /Briefcase, /, '');
replaceInFile('src/components/shared/ClaimHeader.tsx', /ArrowRight, /, '');

// ClaimTimeline.tsx
replaceInFile('src/components/shared/ClaimTimeline.tsx', /statusConfig\[event\.status\]/g, 'statusConfig[event.status || ""]');
replaceInFile('src/components/shared/ClaimTimeline.tsx', /event\.description/g, '(event as any).description');

// glassmorphism-trust-hero.tsx
replaceInFile('src/components/ui/glassmorphism-trust-hero.tsx', /import React from 'react';\n/, '');
replaceInFile('src/components/ui/glassmorphism-trust-hero.tsx', /import \{.*?\} from 'lucide-react';/, "import { ArrowRight, Activity, FileText, CheckCircle } from 'lucide-react';");

// mock/cases.ts
replaceInFile('src/mock/cases.ts', /Patient\[\] = \[/g, 'any[] = [');

// HospitalCaseDetails.tsx
replaceInFile('src/pages/hospital/HospitalCaseDetails.tsx', /MORE_INFORMATION/g, 'MORE_INFO');

// HospitalCases.tsx
replaceInFile('src/pages/hospital/HospitalCases.tsx', /MORE_INFORMATION/g, 'MORE_INFO');

// InsuranceCaseDetails.tsx
replaceInFile('src/pages/insurance/InsuranceCaseDetails.tsx', /MORE_INFORMATION/g, 'MORE_INFO');

// IncomingClaims.tsx
replaceInFile('src/pages/insurance/IncomingClaims.tsx', /import \{ useNavigate \} from 'react-router-dom';/, '');

// RoleSelect.tsx
replaceInFile('src/pages/RoleSelect.tsx', /Cpu, Lock, /g, '');
replaceInFile('src/pages/RoleSelect.tsx', /Shield, Users, BarChart3, Clock, /g, '');
replaceInFile('src/pages/RoleSelect.tsx', /Star, Menu, X, /g, '');
replaceInFile('src/pages/RoleSelect.tsx', /Code2, FileCode, CheckSquare, /g, '');
replaceInFile('src/pages/RoleSelect.tsx', /ChevronUp, ChevronRight, PieChart /g, '');
replaceInFile('src/pages/RoleSelect.tsx', /const \[menuOpen.*?;\n/g, '');
replaceInFile('src/pages/RoleSelect.tsx', /const \[activeStep.*?;\n/g, '');
replaceInFile('src/pages/RoleSelect.tsx', /width=\{32\}/g, 'width={32 as any}');

// claimsApi.ts
replaceInFile('src/services/claimsApi.ts', /import \{ mockClaims \}.*?;\n/, '');
replaceInFile('src/services/claimsApi.ts', /\[\.\.\.mockClaims\]/g, '[]');

// reviewApi.ts
replaceInFile('src/services/reviewApi.ts', /payload: any/g, '_payload: any');

console.log("Fixes applied");
