import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";
import { initializeFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDYyhLUsJlTJ6CsYiKWhxGxSHMoBwm4a_s",
  authDomain: "agrotech-ai-ff555.firebaseapp.com",
  projectId: "agrotech-ai-ff555",
  storageBucket: "agrotech-ai-ff555.firebasestorage.app",
  messagingSenderId: "157651871947",
  appId: "1:157651871947:web:9fc1331f63e9a95e5d934e",
  measurementId: "G-PXX8ME68XL"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
export const auth = getAuth(app);
export const storage = getStorage(app);

// Use initializeFirestore with long polling to bypass potential connection issues
// as requested by "firbase n'est pas connecter"
export const db = initializeFirestore(app, {
  experimentalForceLongPolling: true,
});

export { app, analytics };

