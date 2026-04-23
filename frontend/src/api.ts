import axios from "axios";

const API = import.meta.env.VITE_API_BASE_URL;

export async function fetchExpiries(ticker: string) {
  const res = await axios.get(`${API}/ticker/${ticker}/expiries`);
  return res.data;
}

export async function scanGlobal(data: any) {
  const res = await axios.post(`${API}/scan/global`, data);
  return res.data;
}

export async function scanToday(data: any) {
  const res = await axios.post(`${API}/scan/today`, data);
  return res.data;
}

export async function analyzeTrade(data: any) {
  const res = await axios.post(`${API}/analyze`, data);
  return res.data;
}

export async function fetchHistory(ticker: string) {
  const res = await axios.get(`${API}/history/${ticker}`);
  return res.data;
}