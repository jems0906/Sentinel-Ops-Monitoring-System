FROM node:22-alpine3.22 AS build
WORKDIR /app
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE
RUN apk upgrade --no-cache
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.29-alpine
RUN apk upgrade --no-cache
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
