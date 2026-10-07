FROM node:20-alpine AS build
WORKDIR /app
COPY package.json yarn.lock* ./
# Emergent-only dev tooling (overlay/visual edits) eruit: niet nodig voor de build en
# afhankelijk van assets.emergent.sh. craco.config.js valt netjes terug zonder deze pakketten.
RUN node -e "const f='package.json',p=require('./'+f);for(const k of Object.keys(p.devDependencies||{}))if(k.startsWith('@emergentbase/'))delete p.devDependencies[k];require('fs').writeFileSync(f,JSON.stringify(p,null,2))" \
 && yarn install --network-timeout 600000
COPY . .
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL \
    GENERATE_SOURCEMAP=false
RUN yarn build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
