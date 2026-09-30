import { BrowserRouter } from 'react-router-dom';
import { RoleProvider } from './context/RoleContext';
import { AppRoutes } from './routes/AppRoutes';

function App() {
  return (
    <BrowserRouter>
      <RoleProvider>
        <AppRoutes />
      </RoleProvider>
    </BrowserRouter>
  );
}

export default App;
