import axios from "axios";
console.log(import.meta.env.VITE_API_BASE_URL)
export default axios.create({
  baseURL: 'https://considerate-respect-production.up.railway.app',
  headers: {
    'Authorization': '',
    "Content-Type": "application/json"
  }
});
