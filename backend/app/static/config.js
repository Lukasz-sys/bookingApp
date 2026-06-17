// Frontend i backend działają razem w Dockerze.
// Otwierasz http://localhost:8080, a Nginx przekazuje /api do kontenera FastAPI.
window.BOOKING_API_URL = window.location.origin;
