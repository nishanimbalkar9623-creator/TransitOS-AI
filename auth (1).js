// TransitOS AI Authentication & Client Logic

let supabaseClient = null;
let isLocalFallback = true;

// 1. INITIALIZE SUPABASE CLIENT
if (window.SUPABASE_URL && window.SUPABASE_ANON_KEY &&
    window.SUPABASE_URL !== "YOUR_SUPABASE_URL" &&
    window.SUPABASE_ANON_KEY !== "YOUR_SUPABASE_ANON_KEY") {
  try {
    if (window.supabase) {
      supabaseClient = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY);
      isLocalFallback = false;
      console.log("TransitOS Auth: Supabase client initialized successfully.");
    } else {
      console.warn("TransitOS Auth: Supabase SDK script not found. Using local dev fallback.");
    }
  } catch (error) {
    console.error("TransitOS Auth: Failed to initialize Supabase client:", error);
  }
} else {
  console.log("TransitOS Auth: Supabase keys not set. Running in Local Dev Mode (Offline Mode).");
}

// Seed mock database in localStorage if empty
function seedMockDB() {
  const users = localStorage.getItem('transit_mock_users');
  if (!users) {
    const demoUsers = [
      {
        email: "company@transitos.ai",
        password: "password123",
        name: "Mahindra Logistics Ltd.",
        role: "company"
      },
      {
        email: "truckowner@transitos.ai",
        password: "password123",
        name: "Punjab Road Carrier Corporation",
        role: "truck_owner"
      }
    ];
    localStorage.setItem('transit_mock_users', JSON.stringify(demoUsers));
  }
}
seedMockDB();

// 2. SIGNUP ACTION
async function signUpUser(name, email, password, role) {
  if (!isLocalFallback && supabaseClient) {
    try {
      const { data, error } = await supabaseClient.auth.signUp({
        email: email,
        password: password,
        options: {
          data: {
            full_name: name,
            role: role // 'company' or 'truck_owner'
          }
        }
      });
      if (error) throw error;
      return { success: true, data: data, message: "Signup successful! Please check your email for confirmation, or log in if auto-confirm is enabled." };
    } catch (err) {
      return { success: false, message: err.message };
    }
  } else {
    // Local dev mode fallback
    const users = JSON.parse(localStorage.getItem('transit_mock_users') || '[]');
    const userExists = users.some(u => u.email.toLowerCase() === email.toLowerCase());
    
    if (userExists) {
      return { success: false, message: "An account with this email already exists." };
    }
    
    const newUser = { name, email: email.toLowerCase(), password, role };
    users.push(newUser);
    localStorage.setItem('transit_mock_users', JSON.stringify(users));
    
    // Auto-create local session
    const mockSession = {
      user: {
        email: email.toLowerCase(),
        user_metadata: {
          full_name: name,
          role: role
        }
      }
    };
    localStorage.setItem('transit_session', JSON.stringify(mockSession));
    return { success: true, localMode: true, role: role };
  }
}

// 3. LOGIN ACTION
async function loginUser(email, password) {
  if (!isLocalFallback && supabaseClient) {
    try {
      const { data, error } = await supabaseClient.auth.signInWithPassword({
        email: email,
        password: password
      });
      if (error) throw error;
      
      const role = data.user?.user_metadata?.role || 'company';
      // Store local copy for session guarding
      localStorage.setItem('transit_session', JSON.stringify(data));
      return { success: true, role: role, data: data };
    } catch (err) {
      return { success: false, message: err.message };
    }
  } else {
    // Local dev mode fallback
    const users = JSON.parse(localStorage.getItem('transit_mock_users') || '[]');
    const user = users.find(u => u.email.toLowerCase() === email.toLowerCase() && u.password === password);
    
    if (!user) {
      return { success: false, message: "Invalid email or password. Try demo buttons!" };
    }
    
    const mockSession = {
      user: {
        email: user.email,
        user_metadata: {
          full_name: user.name,
          role: user.role
        }
      }
    };
    localStorage.setItem('transit_session', JSON.stringify(mockSession));
    return { success: true, role: user.role, localMode: true };
  }
}

// 4. LOGOUT ACTION
async function logoutUser() {
  localStorage.removeItem('transit_session');
  if (!isLocalFallback && supabaseClient) {
    await supabaseClient.auth.signOut();
  }
  window.location.href = "login.html";
}

// 5. GET CURRENT USER
function getCurrentUser() {
  const sessionStr = localStorage.getItem('transit_session');
  if (!sessionStr) return null;
  try {
    const session = JSON.parse(sessionStr);
    return session.user;
  } catch (e) {
    return null;
  }
}

// 6. DASHBOARD SESSION GUARD
function guardDashboard(requiredRole) {
  const user = getCurrentUser();
  if (!user) {
    console.warn("Unauthenticated access. Redirecting to login.");
    window.location.href = "login.html";
    return;
  }
  
  const userRole = user.user_metadata?.role;
  if (userRole !== requiredRole) {
    console.warn(`Unauthorized role: ${userRole}. Redirecting to correct dashboard.`);
    if (userRole === 'truck_owner') {
      window.location.href = "truck-dashboard.html";
    } else {
      window.location.href = "company-dashboard.html";
    }
  }
}

// Export variables to global window object for other scripts
window.isLocalFallback = isLocalFallback;
window.supabaseClient = supabaseClient;
window.signUpUser = signUpUser;
window.loginUser = loginUser;
window.logoutUser = logoutUser;
window.getCurrentUser = getCurrentUser;
window.guardDashboard = guardDashboard;
